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
from evidenceforge.reporting import render_report
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


def show_report(state: ResearchState) -> None:
    st.subheader("Research report")
    st.markdown(render_report(state))
    st.caption("Downloads include selected document/source passages. Review before sharing.")
    st.download_button(
        "Download Markdown", render_report(state), "report.md", "text/markdown", on_click="ignore"
    )
    st.download_button(
        "Download JSON", report_export(state), "report.json", "application/json", on_click="ignore"
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
        usage = usage_summary(state)
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
                    "Offline stages use configured allowances; no paid provider calls are made."
                )
            st.json(usage)
            paid = app.paid_usage(owner, thread)
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
            show_report(state)
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


def main(*, public_demo: bool = False) -> None:
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
        st.caption("Local evidence workbench | exact passages and inspectable citations")
        st.info(
            "Choose offline reasoning or configured Gemini. Saved Gemini workflows support "
            "plan approval, editing and resume with durable call records. "
            "Synthetic demos are examples; use documents for your own research."
        )
        directory = load_settings().data_dir
        owner = (
            "hosted"
            if required(load_settings())
            else st.sidebar.text_input("Local workspace scope", value="local")
        )
        st.sidebar.caption(
            "Hosted access uses one trusted owner account."
            if required(load_settings())
            else "Scope names separate local records. Local access is restricted to this computer."
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
        with st.expander("Add local evidence", expanded=False):
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
    with st.form("new_research"):
        question = st.text_area(
            "Research question", value="Compare solar and wind electricity output."
        )
        reasoning = st.selectbox(
            "Reasoning provider", ["Offline"] if public_demo else ["Offline", "Gemini (configured)"]
        )
        live_web = False
        live_energy = False
        if not public_demo:
            st.caption(
                "Gemini sends the question and selected evidence to Google "
                "and uses your configured call/token allowances."
            )
            live_web = st.checkbox("Search live web with Tavily", value=False)
            live_energy = st.checkbox("Include GB half-hour energy API", value=False)
            st.caption(
                "Live search uses configured search credits; the energy API returns GB "
                "generation shares, not annual/global output. Documents are searched "
                "alongside selected live sources."
            )
        demo = st.selectbox(
            "Synthetic scenario (used when no live sources or documents are selected)",
            ["second-pass", "immediate", "empty", "dispute"],
        )
        submitted = st.form_submit_button("Create plan", disabled=app.active(owner))
    if submitted:
        try:
            request = ResearchRequest(
                question=question,
                owner_scope=owner,
                document_ids=tuple(x.strip() for x in entered.splitlines() if x.strip()),
            )
            st.session_state["active_job"] = app.start(
                request,
                demo,
                budget=load_settings().budget,
                gemini=reasoning == "Gemini (configured)",
                live_web=live_web,
                live_energy=live_energy,
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
