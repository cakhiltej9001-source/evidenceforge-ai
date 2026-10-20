"""Streamlit entry point for the local evidence workbench."""

from pathlib import Path
from tempfile import NamedTemporaryFile, gettempdir
from uuid import uuid4

import streamlit as st

from evidenceforge.auth import LoginGate, fingerprint, required
from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.evidence.projection import audit, project
from evidenceforge.exports import report_export
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import PlanDraft
from evidenceforge.report_pdf import PdfExportError, report_pdf
from evidenceforge.reporting import render_report, retained_source_passages, retained_source_text
from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.observability import public_progress, public_timeline
from evidenceforge.services.usage import usage_summary
from evidenceforge.storage.documents import DocumentRecord, DocumentStore
from evidenceforge.workbench import LocalWorkbench


@st.cache_resource  # type: ignore[untyped-decorator]
def workbench(directory: str) -> LocalWorkbench:
    return LocalWorkbench(Path(directory))


def ingest_upload(store: DocumentStore, owner: str, name: str, data: bytes) -> DocumentRecord:
    suffix = Path(name).suffix.lower()
    if suffix not in {".txt", ".pdf", ".docx"} or len(data) > store.options.max_file_bytes:
        raise ValueError("Upload must be a PDF, DOCX or UTF-8 TXT up to 4 MB.")
    folder = store.root / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    path = None
    try:
        with NamedTemporaryFile(dir=folder, suffix=suffix, delete=False) as stream:
            path = Path(stream.name)
            stream.write(data)
        return store.ingest(path, owner)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def show_report(state: ResearchState, export_json: str | None = None) -> None:
    st.subheader("Research report")
    st.markdown(
        render_report(
            state, local_source_links=True, answer_first=True, include_evidence_details=False
        )
    )
    try:
        pdf = report_pdf(state)
    except PdfExportError as exc:
        st.caption(str(exc))
    else:
        st.download_button(
            "Download report PDF", pdf, "research-report.pdf", "application/pdf", on_click="ignore"
        )
    st.caption(
        "The PDF contains the report and source links. Audits and original passages are in JSON."
    )
    show_saved_sources(state)
    st.caption("Downloads include selected document/source passages. Review before sharing.")
    st.download_button(
        "Download Markdown",
        render_report(state, answer_first=True, include_evidence_details=False),
        "report.md",
        "text/markdown",
        on_click="ignore",
    )
    st.download_button(
        "Download JSON",
        export_json or report_export(state),
        "report.json",
        "application/json",
        on_click="ignore",
    )
    with st.expander("Audit results, source ranking and disputes"):
        st.json(audit(state))
    st.subheader("Inspect a finding")
    claims = state["report_claims"]
    if claims:
        cid = st.selectbox(
            "Claim", list(claims), format_func=lambda key: str(claims[key]["statement"])
        )
        graph = project(state, cid)
        for node in graph.nodes:
            if node.kind == "evidence":
                st.text(node.label)
                st.json(
                    {
                        "source_id": node.record.get("source_id"),
                        "locator": node.record.get("locator"),
                    }
                )
            elif node.kind == "source":
                st.text(node.label)
                st.json({k: node.record.get(k) for k in ("url", "document_id", "content_hash")})
        with st.expander("Links, ranking and disagreements"):
            st.json(graph.model_dump(mode="json"))
    else:
        st.info("No audited claims were produced.")


def show_saved_sources(state: ResearchState) -> None:
    snapshot = StateSnapshot.model_validate(state)
    report = snapshot.final_report
    if report is None or not report.source_ids:
        return
    st.subheader("Saved source passages")
    st.caption(
        "Read the retained quotations here if an original website is blocked. "
        "Opening or downloading these passages makes no model or search calls. "
        "These are saved excerpts, not a live or complete copy of the website."
    )
    for index, sid in enumerate(report.source_ids, 1):
        source = snapshot.source_records[sid]
        passages = retained_source_passages(snapshot, sid)
        st.subheader(f"Source [{index}]", anchor=f"saved-source-{index}")
        st.text(source.title)
        if source.access_status == "excerpt_only" or any(
            snapshot.source_acquisitions[aid].content_scope == "search_excerpt"
            or snapshot.source_acquisitions[aid].section is not None
            for evidence in passages
            for aid in evidence.acquisition_ids
        ):
            st.info("Retained search or section excerpts only; full-page access is not verified.")
        with st.expander(f"Read saved passages [{index}]", expanded=index == 1):
            if not passages:
                st.info("No cited passages are available for this source.")
            for evidence in passages:
                locator = evidence.locator
                location = [f"offsets {locator.start_offset}-{locator.end_offset}"]
                if locator.page is not None:
                    location.append(f"page {locator.page}")
                if locator.paragraph is not None:
                    location.append(f"paragraph {locator.paragraph}")
                st.caption("; ".join(location))
                st.code(evidence.passage, language=None, wrap_lines=True)
            if passages:
                st.download_button(
                    f"Download saved passages [{index}]",
                    retained_source_text(snapshot, sid),
                    f"source-{index}-passages.txt",
                    "text/plain",
                    key=f"saved_source_download_{index}",
                    on_click="ignore",
                )


@st.fragment(run_every=2.0)  # type: ignore[untyped-decorator]
def run_panel(app: LocalWorkbench, owner: str) -> None:
    if not authenticated():
        return
    try:
        job = st.session_state.get("active_job")
        if job:
            state = app.result(owner, job)
            if state is not None:
                st.session_state["selected_thread"] = state["thread_id"]
                st.session_state.pop("active_job", None)
        thread = st.session_state.get("selected_thread")
        if not thread:
            if app.active(owner):
                st.info("Creating a plan. Progress will appear here.")
            return
        state = app.snapshot(owner, thread)
        progress = public_progress(state).as_dict()
        st.subheader("Progress")
        st.write({**progress, "approval": state["approval_status"]})
        st.caption("Thread: " + thread)
        s = StateSnapshot.model_validate(state)
        paid = app.paid_usage(owner, thread)
        usage = usage_summary(state, provider_usage=paid)
        if state["approval_status"] == "awaiting_approval":
            st.info("Plan ready. Review it below and choose Approve plan to start research.")
        elif s.run_status == "partial" and s.stop_reason in {"pass_limit", "search_limit"}:
            st.warning(
                "This run reached its research limit. The report contains a partial "
                "answer; unresolved requirements are shown below it."
            )
        if state["tool_errors"]:
            from evidenceforge.services.failures import public_failures

            diagnostics = app.model_failures(owner, thread) or public_failures(state)
            for diagnostic in diagnostics:
                code = diagnostic.get("http_status")
                suffix = f" (HTTP {code})" if code else ""
                st.error(f"{diagnostic['stage']}{suffix}: {diagnostic['message']}")
            st.caption(
                "This run was not retried automatically. A new attempt uses a separate "
                "run allowance; earlier calls remain counted."
            )
            if s.run_status.value in {"failed", "partial"} and any(
                e.kind == "gemini_model" for e in s.events.values()
            ):
                if st.button("Try again with a new Gemini plan", disabled=app.active(owner)):
                    st.session_state["active_job"] = app.retry(owner, thread)
                    st.session_state.pop("selected_thread", None)
                    st.rerun()
                if s.request.document_ids or any(
                    e.kind == "live_retrieval" for e in s.events.values()
                ):
                    st.info(
                        "You can get quoted source passages without Gemini. This uses the "
                        "same selected sources and search allowance, with lexical matching "
                        "instead of model analysis. Review and approve the new plan."
                    )
                    if st.button(
                        "Get source quotations without Gemini", disabled=app.active(owner)
                    ):
                        st.session_state["active_job"] = app.retry(
                            owner, thread, without_gemini=True
                        )
                        st.session_state.pop("selected_thread", None)
                        st.rerun()
        with st.expander("Live timeline"):
            st.table([{"Time": e["time"], "Event": e["step"]} for e in public_timeline(state)])
        with st.expander("Coverage and unresolved questions"):
            st.json(
                {
                    "status": state["coverage_status"],
                    "questions": state["coverage_by_question"],
                    "gaps": state["gaps"],
                }
            )
        with st.expander("Budget and usage"):
            st.write(
                {
                    "Retrieval passes": f"{s.iteration_count}/{s.budget.max_research_passes}",
                    "Report rewrites": f"{s.revision_count}/{s.budget.max_rewrites}",
                    "Model stages": f"{usage['model_attempts']}/{s.budget.max_model_calls}",
                    "Search reservations": (
                        f"{usage['search_reservations']}/{s.budget.max_searches}"
                    ),
                }
            )
            if any(e.get("kind") == "gemini_model" for e in state["events"].values()):
                st.caption(
                    "Gemini usage is saved in durable call receipts. "
                    "Unconfirmed calls are not retried automatically."
                )
            else:
                st.caption(
                    "Offline reasoning makes no Gemini calls. Selected live sources may "
                    "still consume search credits."
                )
            st.json(usage)
            if usage["model_requests_blocked_locally"]:
                st.caption(
                    "Requests blocked locally are workflow attempts, not additional "
                    "Gemini calls or unknown provider charges."
                )
            if paid is not None:
                st.write("Gemini provider usage")
                st.json(paid)

        active = app.active(owner)
        if state["run_status"] in {"created", "running"}:
            if st.button("Cancel research", disabled=state["run_status"] == "created"):
                app.cancel(owner, thread)
                if not active:
                    st.session_state["active_job"] = app.resume(owner, thread)
                st.info("Cancellation requested.")
            if state["approval_status"] == "awaiting_approval":
                st.subheader("Review the research plan")
                for question in state["research_questions"]:
                    st.text(str(question["question"]))
                    st.write(question["acceptance_criteria"])
                st.caption("Plan version: " + str(state["plan_version"]))
                with st.expander("Edit the plan"):
                    with st.form(f"edit_plan_{thread}_{state['plan_version']}"):
                        rows = [
                            {
                                "Question": q.question,
                                "Criteria": "; ".join(q.acceptance_criteria),
                                "Importance": q.importance,
                            }
                            for q in s.research_questions
                        ]
                        edited_rows = st.data_editor(
                            rows,
                            num_rows="dynamic",
                            hide_index=True,
                            column_config={
                                "Criteria": st.column_config.TextColumn(
                                    "Acceptance criteria (semicolon separated)"
                                ),
                                "Importance": st.column_config.NumberColumn(
                                    min_value=0.05, max_value=1.0
                                ),
                            },
                            key=f"plan_rows_{thread}_{state['plan_version']}",
                        )
                        save_edit = st.form_submit_button("Save edited plan", disabled=active)
                    if save_edit:
                        try:
                            plan = PlanDraft.model_validate(
                                {
                                    "questions": [
                                        {
                                            "question": row["Question"],
                                            "acceptance_criteria": [
                                                c.strip()
                                                for c in row["Criteria"].split(";")
                                                if c.strip()
                                            ],
                                            "importance": row["Importance"],
                                        }
                                        for row in edited_rows
                                    ]
                                }
                            )
                            st.session_state["active_job"] = app.edit(
                                owner, thread, plan, state["plan_version"]
                            )
                            st.info(
                                "Edited plan saved for renewed review. "
                                "Approve its new version to continue."
                            )
                        except Exception:
                            st.error(
                                "Use focused, distinct questions with nonempty criteria "
                                "and valid importance. "
                                "Keep the plan within its subquestion allowance."
                            )
                left, right = st.columns(2)
                if left.button("Approve plan", disabled=active):
                    st.session_state["active_job"] = app.resume(
                        owner,
                        thread,
                        PlanDecision(approved=True, plan_version=state["plan_version"]),
                    )
                if right.button("Reject plan", disabled=active):
                    st.session_state["active_job"] = app.resume(
                        owner,
                        thread,
                        PlanDecision(approved=False, plan_version=state["plan_version"]),
                    )
            elif not active and st.button("Resume saved workflow"):
                st.session_state["active_job"] = app.resume(owner, thread)
        else:
            show_report(state, app.export(owner, thread))
    except Exception:
        # Provider, filesystem and validation exceptions may include sensitive values.
        st.error(
            "The local operation could not finish. "
            "Check the selected scope and workflow configuration."
        )
        st.session_state.pop("active_job", None)


@st.cache_resource  # type: ignore[untyped-decorator]
def login_gate() -> LoginGate:
    return LoginGate()


def authenticated() -> bool:
    settings = load_settings()
    if not required(settings):
        return True
    try:
        identity = fingerprint(settings)
    except ConfigurationError:
        st.error("Hosted login is not configured. Ask the owner to complete setup.")
        return False
    if st.session_state.get("login_identity") == identity:
        return True
    st.subheader("Sign in to EvidenceForge")
    with st.form("hosted_login", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        if login_gate().check(username, password, settings):
            st.session_state["login_identity"] = identity
            st.rerun()
        st.error(
            "Sign-in failed or temporarily limited. Check your details and try again in a minute."
        )
    return False


def main(*, public_demo: bool = False, cloud_hosted: bool = False) -> None:
    st.set_page_config(page_title="EvidenceForge", page_icon="🔎", layout="wide")
    if not authenticated():
        return
    st.title("EvidenceForge research workbench")
    if required(load_settings()) and st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    if public_demo:
        st.caption("Public demonstration | exact passages and inspectable citations")
        st.info(
            "Try the workflow with offline synthetic examples. No Gemini calls or search "
            "credits are used. This is a demonstration, not a verified research answer. "
            "Saved runs are temporary and belong to this browser session; download your "
            "report before leaving. Use the local app for documents and live research."
        )
        directory = Path(gettempdir()) / "evidenceforge-community-demo"
        owner = st.session_state.setdefault("public_demo_owner", "visitor_" + uuid4().hex)
        st.sidebar.caption("Temporary storage for this browser session only.")
    else:
        st.caption(
            "Hosted live research | exact passages and inspectable citations"
            if cloud_hosted
            else "Local evidence workbench | exact passages and inspectable citations"
        )
        st.info(
            "Choose offline reasoning or configured Gemini. Saved Gemini workflows support "
            "plan approval, editing and resume with durable call records. "
            "Synthetic demos are examples; use documents for your own research."
        )
        directory = (
            Path(gettempdir()) / "evidenceforge-community-live"
            if cloud_hosted
            else load_settings().data_dir
        )
        if cloud_hosted:
            st.warning(
                "Hosting is free; Gemini and Tavily may consume your provider allowance. "
                "Hosted files and saved research are temporary. Download reports before "
                "leaving; use the local app for durable storage."
            )
        if cloud_hosted and not required(load_settings()):
            owner = st.session_state.setdefault("cloud_visitor_owner", "visitor_" + uuid4().hex)
            st.sidebar.caption("Temporary research for this browser session only.")
        else:
            owner = (
                "hosted"
                if required(load_settings())
                else st.sidebar.text_input("Local workspace scope", value="local")
            )
            st.sidebar.caption(
                "Hosted access uses one trusted owner account."
                if required(load_settings())
                else (
                    "Scope names separate local records. "
                    "Local access is restricted to this computer."
                )
            )
    app = workbench(str(directory.resolve()))
    try:
        ResearchRequest(question="Workspace selection", owner_scope=owner)
    except Exception:
        st.error("Enter a valid workspace scope.")
        return
    if st.session_state.get("current_owner") != owner:
        for key in ("active_job", "selected_thread", "document_ids"):
            st.session_state.pop(key, None)
        st.session_state["current_owner"] = owner
    entered = ""
    if not public_demo:
        with st.expander("Add document evidence", expanded=False):
            upload = st.file_uploader("PDF, DOCX or TXT, up to 4 MB", type=["pdf", "docx", "txt"])
            if st.button("Import document", disabled=upload is None):
                try:
                    assert upload is not None
                    record = ingest_upload(
                        DocumentStore(app.data_dir / "documents"),
                        owner,
                        upload.name,
                        upload.getvalue(),
                    )
                    ids = st.session_state.setdefault("document_ids", [])
                    if record.id not in ids:
                        ids.append(record.id)
                    st.success("Imported document: " + record.id)
                    if record.warnings:
                        st.write(record.warnings)
                except Exception:
                    st.error("Document import failed. Check format, text content and size.")
            entered = st.text_area(
                "Existing document IDs (one per line)",
                value="\n".join(st.session_state.get("document_ids", [])),
            )
    synthetic_mode = public_demo
    if not public_demo:
        synthetic_mode = (
            st.radio(
                "Research mode",
                ["Research with real sources", "Synthetic demonstration"],
                horizontal=True,
            )
            == "Synthetic demonstration"
        )
        if synthetic_mode:
            st.info(
                "Synthetic demonstration uses example passages and offline reasoning. "
                "It cannot answer general factual questions."
            )
        else:
            st.caption(
                "Select Tavily web search or imported documents. "
                "Gemini does not search the web by itself."
            )
    allow_revision = False
    with st.form("new_research"):
        st.caption("Explain a topic · Compare ideas · Explore your documents")
        question = st.text_area(
            "Research question",
            value="",
            height=140,
            placeholder=("What would you like to find out?\nType your question in your own words."),
            help="Add a location, time period or comparison for a more focused answer.",
        )
        reasoning = st.selectbox(
            "Reasoning provider",
            ["Offline"] if synthetic_mode else ["Offline", "Gemini (configured)"],
            index=(
                1
                if not synthetic_mode
                and load_settings().model_provider == "gemini"
                and load_settings().model_api_key is not None
                else 0
            ),
        )
        live_web = False
        if not synthetic_mode:
            st.caption(
                "Gemini sends the question and selected evidence to Google "
                "and uses your configured call/token allowances."
            )
            st.caption(
                "If Gemini is unavailable, select Offline and keep Tavily enabled to get "
                "quotations from real web sources without Gemini calls."
            )
            st.caption(
                "Gemini reviews and plans in one call. The first search uses the approved "
                "plan, leaving room for a revision and review within six model calls."
            )
            live_web = st.checkbox(
                "Search live web with Tavily",
                value=load_settings().tavily_api_key is not None,
            )
            st.caption(
                "Live search uses configured search credits. Documents are searched "
                "alongside selected web sources."
            )
        if not public_demo:
            limits = load_settings().budget
            if not synthetic_mode:
                allow_revision = st.checkbox(
                    "Allow one report revision within the call limit",
                    value=True,
                    help="A revision and its review need two remaining calls. "
                    "The model-call, token and search limits stay unchanged.",
                )
                if limits.max_model_calls < 6:
                    st.caption("This call limit may leave no room for a full revision and review.")
            st.caption(
                f"Per run: up to {limits.max_model_calls} model calls and "
                f"{limits.max_searches} searches. Review the plan before continuing."
            )
        demo = "second-pass"
        if synthetic_mode:
            demo = st.selectbox(
                "Synthetic scenario",
                ["second-pass", "immediate", "empty", "dispute"],
            )
        submitted = st.form_submit_button("Create plan", disabled=app.active(owner))
    if submitted and not question.strip():
        st.error("Type a research question to get started. No API calls were made.")
    elif submitted:
        try:
            request = ResearchRequest(
                question=question,
                owner_scope=owner,
                document_ids=(
                    ()
                    if synthetic_mode
                    else tuple(x.strip() for x in entered.splitlines() if x.strip())
                ),
            )
            if not synthetic_mode and not (request.document_ids or live_web):
                st.error(
                    "No research sources selected. Enable Search live web with Tavily "
                    "or import a document, then click Create plan. Gemini does not search "
                    "the web by itself. No API calls were made for this submission."
                )
            else:
                st.session_state["active_job"] = app.start(
                    request,
                    demo,
                    budget=(
                        load_settings().budget.model_copy(
                            update={"max_rewrites": 1 if allow_revision else 0}
                        )
                        if not synthetic_mode
                        else load_settings().budget
                    ),
                    gemini=reasoning == "Gemini (configured)",
                    live_web=live_web,
                    live_energy=False,
                )
                st.session_state.pop("selected_thread", None)
        except ConfigurationError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Provide a specific research question and valid document IDs. "
                "Another operation may be active."
            )
    with st.sidebar:
        st.subheader("Reconnect")
        try:
            threads = app.threads(owner)
            if threads:
                selected = st.selectbox("Saved thread", threads)
                if st.button("Open saved run"):
                    st.session_state["selected_thread"] = selected
                    st.session_state.pop("active_job", None)
        except Exception:
            st.error("Saved workflows are unavailable in this scope.")
    run_panel(app, owner)


if __name__ == "__main__":
    main()
