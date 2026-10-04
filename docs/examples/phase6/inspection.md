# Evidence inspection

Exact retained quotations and heuristic judgments; rankings are not truth probabilities.

| ID / kind | Retained record |
|---|---|
| question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a / question | What was Northfield solar electricity output? |
| claim_38ab5c62eac859cb6d9d6adb989d21e69a1ff521bcd244a6ef192992b07948ed / claim | Northfield solar electricity output was 100 GWh in 2024 for all plants under standard operation\. |
| claim_47835937afaf92534f593f736367b82f00619964d4a42e014125064c04ed515b / claim | Northfield solar electricity output was 900 GWh in 2023 for all plants under standard operation\. |
| claim_934217c0fc872744ee39eaf551343f40924b002d03959dac040ec6641144c380 / claim | Northfield solar electricity output was 100 GWh in 2024 for all plants under standard operation\. |
| claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 / claim | Northfield solar electricity output was 120 GWh in 2024 for all plants under standard operation\. |
| claim_d0218755e625165597b6fcc4f6afc6ee19f6a598ddc521224a40029aec203533 / claim | Northfield solar electricity output was 100000 MWh in 2024 for all plants under standard operation\. |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 / evidence | Northfield solar electricity output was 100000 MWh in 2024 for all plants under standard operation\.; snapshot artifact\_cf6c760b49249c825ee5acb8b8a0743853d27f6e679578680f58da2894dd6012; offsets 0:99 |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 / evidence | Northfield solar electricity output was 100 GWh in 2024 for all plants under standard operation\.; snapshot artifact\_c9be91e62e1094a9455e6be6301d2c4aadfd2133dd679cfe8ead5b992a669d79; offsets 0:96 |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 / evidence | Northfield solar electricity output was 100 GWh in 2024 for all plants under standard operation\.; snapshot artifact\_c9be91e62e1094a9455e6be6301d2c4aadfd2133dd679cfe8ead5b992a669d79; offsets 0:96 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db / evidence | Northfield solar electricity output was 120 GWh in 2024 for all plants under standard operation\.; snapshot artifact\_66bd184032be9e32b65a9c97766020bd45a34e63b4cac8cc33fe43c6871f193c; offsets 0:96 |
| evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 / evidence | Northfield solar electricity output was 900 GWh in 2023 for all plants under standard operation\.; snapshot artifact\_fb707703f763e3fbfe4448863559c768d99a2a871d29d6f56505bbe4bd00c344; offsets 0:96 |
| source_788a873729764ce7edd64eec6f2ae61e8ae78c5a2032985304d6a0076d4d6dbe / source | Synthetic historical; https://historical\.example\.org/energy; hash d5021bb8f59104e70e505c3f96aa06e10853f5d7eb269b73e1c52740942d0a38 |
| source_956212a3790b7f4f606f0628bf81388a20577ebd6cab99dc6acd19ab3980bebf / source | Synthetic primary; https://primary\.example\.org/energy; hash 5036768b7be128cf1b27d558182f90c2e26de9c4d279f750d3b4d410bcf54000 |
| source_b6e936d3389db91d88e1e36307a7ffad1cdd599f153cda9ec190d564660fcd28 / source | Synthetic secondary; https://secondary\.example\.org/energy; hash 4fc6eb9c8d331b0761b5b2b48e794dc488e5ae92db5cced5f37e3a5ced6982c0 |
| source_ba210b1000e58c26c3cde745d9a1e76538848f38b51a87467f6b6b9756e979f7 / source | Synthetic units; https://units\.example\.org/energy; hash eb94f3c54699536cc168a4d5017b23459d115b7902c91354238bce15ecea55a3 |
| source_e2e7be0c719af4759092f8cd64b55a417febbb5930f05ac866afbddb6c51af25 / source | Synthetic copy; https://copy\.example\.org/energy; hash 5036768b7be128cf1b27d558182f90c2e26de9c4d279f750d3b4d410bcf54000 |

| From | Relationship | To | Rationale / record |
|---|---|---|---|
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | contextualizes | evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | Different timeframe; no contradiction inferred\.; comparison_ba5a319af9ad5dc308085c09f5069b02ee0b036a3df4017ae1d129800b9f55d8 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | contextualizes | evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | Different timeframe; no contradiction inferred\.; comparison_ca251f519332cf5af8898abe5c9271a44d54af14f4f135167d0eea90c0e66e18 |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | contextualizes | evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | Different timeframe; no contradiction inferred\.; comparison_0b5350a0f7eb3350d02ddf8cc539711b8db2ed5d124488f8bc971eb066cbfc4b |
| claim_47835937afaf92534f593f736367b82f00619964d4a42e014125064c04ed515b | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Claim was assigned to this research question\.; derived |
| claim_d0218755e625165597b6fcc4f6afc6ee19f6a598ddc521224a40029aec203533 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Claim was assigned to this research question\.; derived |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Lexical question overlap; not factual verification\.; derived |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | contradicts | claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_4448ca9b60c3e6cd8f8eb520025f58615e2ee002308d6454c499b2ca69a5b336 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | contradicts | claim_d0218755e625165597b6fcc4f6afc6ee19f6a598ddc521224a40029aec203533 | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_99186d1391270a5db4778940373b2ca9586f3ea7ceb0b63db10f1684e9708338 |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | supports | claim_d0218755e625165597b6fcc4f6afc6ee19f6a598ddc521224a40029aec203533 | Exact retained passage match\.; link_b3c766627f66dd2687b8003677293d72627fb6a763cf78d07f1e1152c1df0188 |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | contradicts | claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_e0a02e381e9e17efd44cfa4342d5bcec1fc183270b3cd6dec550e0ac3aa83ca9 |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | contradicts | evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | Unequal numeric values under the same scope; unresolved without a vote decision\.; comparison_16dceaeac5b1e133219790a2ab6392a244b5080f4b5fce6b45ee02144dab2a3e |
| evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Lexical question overlap; not factual verification\.; derived |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Lexical question overlap; not factual verification\.; derived |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | contradicts | evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | Unequal numeric values under the same scope; unresolved without a vote decision\.; comparison_28c689e9ee79ad78ab1911ebfacdf83ee638209717cadc2b31d1ac40eb5521b0 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | contradicts | claim_934217c0fc872744ee39eaf551343f40924b002d03959dac040ec6641144c380 | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_137755fb308d3420015d516650b9ff6a79cd02e597c683bf194f48c72933be7a |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | contradicts | evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | Unequal numeric values under the same scope; unresolved without a vote decision\.; comparison_cd80d66a0fea6b82a8dc0177e96fa1efdc7fa5023588c66ad57ea9b109aad63d |
| claim_934217c0fc872744ee39eaf551343f40924b002d03959dac040ec6641144c380 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Claim was assigned to this research question\.; derived |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | contextualizes | evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | Different timeframe; no contradiction inferred\.; comparison_64b3cc1ae0421e17acd498170fc3c61952dcc9c93eb861eb1488d57e89198732 |
| claim_38ab5c62eac859cb6d9d6adb989d21e69a1ff521bcd244a6ef192992b07948ed | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Claim was assigned to this research question\.; derived |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | supports | claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 | Exact retained passage match\.; link_3edb0d360ea094d1248f5bbaa090666b7c384d08e8d7cc03b6ee212c5afd648f |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | duplicate_of | evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | Identical normalized quotation; independent corroboration is not established\.; comparison_31c7ce20ba5c5cc8eb01a605cd16b7fed7663eccb410465b0d399fd1e7556c1b |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | supports | claim_38ab5c62eac859cb6d9d6adb989d21e69a1ff521bcd244a6ef192992b07948ed | Exact retained passage match\.; link_0de915b2716c8e6c9275bdfdd5a57f0454058bf3447e22b72fc1bcf8ac22d445 |
| claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Claim was assigned to this research question\.; derived |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | retrieved_from | source_956212a3790b7f4f606f0628bf81388a20577ebd6cab99dc6acd19ab3980bebf | Exact retained passage and source version\.; derived |
| source_e2e7be0c719af4759092f8cd64b55a417febbb5930f05ac866afbddb6c51af25 | duplicate_of | source_956212a3790b7f4f606f0628bf81388a20577ebd6cab99dc6acd19ab3980bebf | Same family or retained content; independent votes are not established\.; derived |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | contradicts | claim_bfbe459c57e7e997a40d9c0a5b0fdbf153ee01ee862fd924b0738c3ccdb20e50 | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_a52362f1b1b3079d8d8062e41d55a82e559ec351fe4133209a33b837aeaf147c |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Lexical question overlap; not factual verification\.; derived |
| evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | retrieved_from | source_ba210b1000e58c26c3cde745d9a1e76538848f38b51a87467f6b6b9756e979f7 | Exact retained passage and source version\.; derived |
| evidence_67b317ae22864228210c1581dbbbc8f56ffeebdd9cc875f576fcdd12300dd379 | supports | evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | Equal numeric values after unit conversion under the same explicit scope\.; comparison_d486452f57c4b0b3a05cbc60aa4bf14c9ee03a2d4394e930c3b86aac458dd948 |
| evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | retrieved_from | source_788a873729764ce7edd64eec6f2ae61e8ae78c5a2032985304d6a0076d4d6dbe | Exact retained passage and source version\.; derived |
| evidence_993a4e16df625975ef53be24f319808f3a234aafd07a3d8a653c5b41f6e4cdd6 | supports | claim_47835937afaf92534f593f736367b82f00619964d4a42e014125064c04ed515b | Exact retained passage match\.; link_0530d38ceb876a430d4085b93055941ea6650a5895d51eda0253c1807380fb54 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | addresses | question_a840fa79cde89f49191e7be5c7f64f058b816c9c591e4e089458934ca28e6d5a | Lexical question overlap; not factual verification\.; derived |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | retrieved_from | source_e2e7be0c719af4759092f8cd64b55a417febbb5930f05ac866afbddb6c51af25 | Exact retained passage and source version\.; derived |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | supports | claim_934217c0fc872744ee39eaf551343f40924b002d03959dac040ec6641144c380 | Exact retained passage match\.; link_c24498de44ec4775e4a92764cf4aad4d726a7cd741e170918799e6f214bb5f53 |
| evidence_2a54b5ba2e6ae418332ad9aa493943c2c8853eb53bbe2fa96d0c5320ac7ae122 | supports | evidence_1049df6fe0fd5135f72e229f0035586183b123024a2316e798f4cc664b8649b7 | Equal numeric values after unit conversion under the same explicit scope\.; comparison_c00ab13fe7ff0c20c3128804158de4b425e683a488e07764362dd50c3bbfb1f8 |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | retrieved_from | source_b6e936d3389db91d88e1e36307a7ffad1cdd599f153cda9ec190d564660fcd28 | Exact retained passage and source version\.; derived |
| evidence_849a78c5f8db2c7326642348e2c3a9aa906b3db6337ddc2ec363ca1797a330db | contradicts | claim_38ab5c62eac859cb6d9d6adb989d21e69a1ff521bcd244a6ef192992b07948ed | Unequal numeric values under the same scope; unresolved without a vote decision\.; link_1aced1b72885a9a07b313826bcb8bb2bdab97f4a4a8ffeb149492930c09741f5 |

## Source ranking

Unknown features use a neutral value of 0.5. Family copies do not count as independent votes.

| Source | Heuristic score | Known weight | Features: value Ã— weight |
|---|---|---|---|
| source_ba210b1000e58c26c3cde745d9a1e76538848f38b51a87467f6b6b9756e979f7 | 0.941 | 1.000 | relevance: 1.0 x 0.35; primary_evidence: 1.0 x 0.25; publisher_identity: 1.0 x 0.1; methodology: 1.0 x 0.1; recency: 0.825 x 0.05; independent_corroboration: 0.5 x 0.1; family_uniqueness: 1.0 x 0.05 |
| source_956212a3790b7f4f606f0628bf81388a20577ebd6cab99dc6acd19ab3980bebf | 0.916 | 1.000 | relevance: 1.0 x 0.35; primary_evidence: 1.0 x 0.25; publisher_identity: 1.0 x 0.1; methodology: 1.0 x 0.1; recency: 0.825 x 0.05; independent_corroboration: 0.5 x 0.1; family_uniqueness: 0.5 x 0.05 |
| source_e2e7be0c719af4759092f8cd64b55a417febbb5930f05ac866afbddb6c51af25 | 0.575 | 1.000 | relevance: 1.0 x 0.35; primary_evidence: 0.0 x 0.25; publisher_identity: 1.0 x 0.1; methodology: 0.0 x 0.1; recency: 0.992 x 0.05; independent_corroboration: 0.5 x 0.1; family_uniqueness: 0.5 x 0.05 |
| source_788a873729764ce7edd64eec6f2ae61e8ae78c5a2032985304d6a0076d4d6dbe | 0.550 | 1.000 | relevance: 1.0 x 0.35; primary_evidence: 0.0 x 0.25; publisher_identity: 1.0 x 0.1; methodology: 0.0 x 0.1; recency: 0.992 x 0.05; independent_corroboration: 0.0 x 0.1; family_uniqueness: 1.0 x 0.05 |
| source_b6e936d3389db91d88e1e36307a7ffad1cdd599f153cda9ec190d564660fcd28 | 0.550 | 1.000 | relevance: 1.0 x 0.35; primary_evidence: 0.0 x 0.25; publisher_identity: 1.0 x 0.1; methodology: 0.0 x 0.1; recency: 0.992 x 0.05; independent_corroboration: 0.0 x 0.1; family_uniqueness: 1.0 x 0.05 |

## Analysis limits

- 5 of 5 passages matched numeric scope grammar; other passages remain unclassified\.

## Unresolved gaps

- Reconcile retained values 100000000000 versus 120000000000 Wh: northfield solar electricity output in 2024 for all plants under standard operation
- Reconcile retained values 100000000000 versus 120000000000 Wh: northfield solar electricity output in 2024 for all plants under standard operation
