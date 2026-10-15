# Spec vs. current build

Compares `docs/product-spec.md` (Jewellery Image Studio v1.0, the source of truth) with the code and prototype as of commit `8403a71`. Where they disagree, the spec wins unless the founder decides otherwise.

## Direct conflicts (built differently from the spec)

| Area | Spec says | Current build | Spec § |
|---|---|---|---|
| Sign-in | Registration and sign-in are required | Guest account on first open, no sign-in | 9.1 |
| What a credit pays for | Credits are spent per **generation**; cost shown before each one; first image generated after the user confirms | Previews are free; credits are spent per **download**; 5 images start automatically on upload | 9.4, 9.7, 12.2 |
| Number of images | One image by default; more only on a separate, priced action | 1 white + 4 marble automatically | 9.4 |
| Category | User selects category; it is a required product field | Category optional ("auto"), metal auto-detected | 8, 9.3 |
| Fidelity claims | Never claim guaranteed accuracy; user must verify | UI says "Your piece is unchanged" and "Product match checked" | 4, 9.5 |
| Marketplace claims | Only label a preset marketplace-ready once requirements are verified and documented | Prototype says "Amazon · Flipkart ready"; code comment says "as marketplaces require" | 7.1, 13.2 |
| Image types | V1 = catalogue + marketplace only; luxury and lifestyle deferred | Velvet tray, Silk drape and Festive presets look like luxury or lifestyle styling | 7 |
| Unstated policies | Credit expiry, receipts undecided | Prototype promises "Credits never expire" and "GST invoice" | 9.7, 18 |
| Name | Jewellery Image Studio | "Lustre" (placeholder) | header |

## Missing (in the spec, not built)

- **Product catalogue:** named product records, rename, delete, browse a product's image history (§9.3). We have unnamed "shoots" with no delete.
- **Review actions:** Accept, report a product-detail issue (8 categories), report a visual-quality issue (6 categories), with reports stored for analysis (§9.5).
- **Quality-failure refunds:** a credit refund when a user reports a changed jewellery detail (§12.3). We only refund technical failures.
- **Deletion and privacy:** delete source photos, outputs and products; documented retention covering caches, backups and external processing (§9.8, §14).
- **Hindi:** onboarding and interface in English and Hindi (§15).
- **Onboarding:** a guided first-generation walkthrough (§15).
- **Verified marketplace presets:** a spec record per marketplace with source and verification date (§13.2).
- **Evaluation dataset:** the 10–20 item fidelity test set, severity labels (critical / major / minor / presentation-only) and a launch quality gate (§10.5–10.7, §11).
- **Native share:** share to WhatsApp and other apps from the phone (§9.6). This belongs to the mobile app, which isn't built yet.

## Already aligned

- **Fidelity approach:** strict product fidelity through compositing the real product pixels; the AI only changes background, lighting and framing (§10.2).
- **Before-and-after:** side-by-side compare with the original (§9.5).
- **Technical failures:** automatic credit refund, plus idempotent charges so there are no duplicates (§9.7, §19).
- **Photo guidance:** plain-language tips for blurry, dark, cropped or small photos, while still accepting a single usable photo (§9.2).
- **Optional angles:** additional angles are optional, with up to 4 photos (§9.2).
- **Aspect ratios:** multiple ratios are supported (§9.6).
- **Privacy:** users can only see their own content, and the tests check this (§9.1, §14).
- **Model-worn:** model-worn photography is disabled ("coming soon") (§7.2).
- **No training:** no custom model training (§1, §11.5).
- **Pricing:** prices are left as placeholders until validated (§12.4).
- **Tech stack:** the spec leaves it undecided. The current Replicate + BiRefNet setup should be treated as a **provisional baseline** for the §16.4 Phase 3 evaluation, not a final choice; providers are swappable in `providers.py`.
