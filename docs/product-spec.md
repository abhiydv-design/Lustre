# Jewellery Image Studio

## Detailed Product Specification, MVP Scope, and Image Evaluation Plan

**Document status:** Detailed working specification based on founder
decisions\
**Product name:** Jewellery Image Studio\
**Product category:** AI-assisted jewellery product photography\
**Launch market:** India\
**Primary platform:** Mobile app\
**Business ambition:** Commercial startup\
**Business model:** Free trial followed by paid credit packs\
**Technology stack and AI provider:** Undecided; intentionally not
selected in this document\
**Version:** 1.0 --- Product scope and validation draft

------------------------------------------------------------------------

# 1. Executive Summary

Jewellery Image Studio is a mobile app that helps jewellery sellers
create professional, commerce-ready images of their actual jewellery
using ordinary phone photos. The goal is to reduce the cost, effort, and
delay associated with traditional product photography while preserving
the real design of the item being sold.

A user uploads a photo of a jewellery item, chooses a catalogue or
marketplace image style, generates one image, compares the result with
the source, and accepts, reports, or regenerates it. Users can create
additional variations by spending additional credits. The app includes
accounts, saved image history, and product catalogue management from day
one.

The product is intended to serve all major customer segments: local
jewellers, independent shops, Instagram and WhatsApp sellers, D2C and
online brands, manufacturers, wholesalers, and marketplace sellers. All
major jewellery categories are in the intended scope.

The defining product requirement is **strict product fidelity**. The
system should improve the presentation of the uploaded jewellery without
intentionally redesigning it. Changes to background, lighting, framing,
and visual preset are allowed; changes to the jewellery's defining
physical details are not an intended transformation.

## Version 1 focus

Included: - Catalogue product photography - Marketplace-ready product
imagery - Phone photo capture and upload - One required image with
optional additional angles - Background, lighting, framing, and
preset-style controls - One initial generated image, with optional paid
variations - Side-by-side original/result comparison - User acceptance
and product-detail issue reporting - Regeneration and credit refunds
under defined failure policies - Multiple aspect ratios and verified
marketplace export presets - Accounts, product catalogue management, and
saved image history - English and Hindi onboarding and interface -
Download and native sharing - Free trial and paid credit packs

Deferred: - Luxury campaign photography - Lifestyle and model-worn
imagery - Video and animation - Bulk generation and bulk imports -
Direct marketplace/social publishing - Team workspaces and advanced
collaboration - Advanced manual editing - Custom prompts that
substantially transform the product

The immediate objective is not to train a custom AI model by default. It
is to establish a high-quality evaluation dataset and determine whether
available image-generation approaches can satisfy fidelity, usability,
cost, and speed requirements. Fine-tuning or other specialised training
should only be considered after evidence shows it is needed and suitable
data rights and paired examples are available.

------------------------------------------------------------------------

# 2. Problem Statement

Jewellery sellers need high-quality images for product listings,
catalogues, social commerce, WhatsApp selling, and other marketing
channels. Traditional jewellery photography may require a photographer,
specialist lighting, equipment, models, retouching, and repeated shoots
for different products or campaigns.

This creates several problems: 1. **Cost:** Professional photography may
be too expensive for small sellers or large catalogues. 2. **Time:**
Organising and completing a shoot can delay listings and campaigns. 3.
**Operational effort:** Sellers may not have photography skills,
equipment, or studio access. 4. **Consistency:** Images from different
shoots may have different backgrounds, lighting, and framing. 5.
**Channel requirements:** The same item may need different crops, aspect
ratios, or presentation styles. 6. **AI trust:** Generic image
generation can alter the actual jewellery, creating a misleading
representation of the item being sold.

The product must solve the cost and workflow problem without undermining
buyer trust through product inaccuracies.

------------------------------------------------------------------------

# 3. Vision, Mission, and Value Proposition

## 3.1 Vision

Make professional jewellery product photography accessible to jewellery
businesses of different sizes.

## 3.2 Mission

Help sellers turn everyday phone photos into polished product images
that are easier to use across e-commerce and social-selling workflows.

## 3.3 Core promise

**Create professional images of your actual jewellery without the cost
and logistics of a traditional photoshoot.**

This promise must be supported by validation. The product should not
claim perfect accuracy until quality tests demonstrate that it can meet
a defined standard.

## 3.4 Value by customer type

### Local and independent jewellers

-   Create listing images without arranging a professional shoot for
    every product.
-   Keep a basic catalogue of products and images.
-   Download and share images with customers.

### Instagram and WhatsApp sellers

-   Produce attractive images quickly.
-   Save images for reuse in future customer conversations.
-   Share images through the phone's native sharing options.

### D2C and online jewellery brands

-   Improve consistency across product listings.
-   Generate multiple framing options for different sales channels.
-   Organise outputs by product.

### Manufacturers and wholesalers

-   Create product-focused images across a broad range of items.
-   Maintain a record of source photos and generated images.
-   Potentially expand to higher-volume workflows in a later phase.

### Marketplace sellers and resellers

-   Prepare images for supported marketplace requirements.
-   Reuse verified export presets.
-   Avoid manually recreating every crop and framing variation.

All customer segments are in scope from day one. A first pilot
recruitment priority remains an open business decision.

------------------------------------------------------------------------

# 4. Product Principles

1.  **Preserve the product.** The app must not intentionally redesign
    the jewellery.
2.  **Presentation can change; identity should not.** Background,
    lighting, framing, and preset styling may change while defining
    product details remain faithful.
3.  **Keep the workflow approachable.** Users should not need
    professional photography or editing skills.
4.  **Be honest about limitations.** A generated image must be reviewed;
    an output should not be described as guaranteed exact.
5.  **Make costs visible.** Credit charges must be shown before
    generation.
6.  **Treat errors fairly.** Technical generation failures automatically
    return credits; reported incorrect jewellery details qualify for a
    credit refund under the agreed policy.
7.  **Keep customer assets private.** Product images may reveal valuable
    inventory or unreleased designs.
8.  **Make catalogue work reusable.** Products and images should remain
    organised in the user's account until deleted.
9.  **Support real selling workflows.** Exports should use verified
    requirements rather than vague claims of marketplace compliance.
10. **Validate before expanding.** Add more complex image types only
    after the initial workflow meets quality requirements.

------------------------------------------------------------------------

# 5. Target Customers and Scope

## 5.1 Customer segments included from day one

-   Local jewellery shops and independent jewellers
-   Instagram and WhatsApp jewellery sellers
-   D2C and online jewellery brands
-   Manufacturers and wholesalers
-   Marketplace sellers and resellers

The app should provide one common core workflow rather than a separate
product for each segment.

## 5.2 Open customer research questions

-   Which segment has the most urgent photography problem?
-   How frequently does each segment create new product images?
-   How much does each segment currently spend on photography?
-   Which sales channels are most important to each segment?
-   What level of fidelity do users expect before trusting an output?
-   How much would users pay for one accepted image?
-   Which segments are most likely to purchase credit packs repeatedly?

These questions should be answered through interviews and pilot usage,
not assumptions.

------------------------------------------------------------------------

# 6. Jewellery Category Coverage

All major jewellery categories are intended to be supported:

-   Rings
-   Earrings
-   Necklaces
-   Pendants
-   Bracelets
-   Bangles
-   Chains
-   Anklets
-   Jewellery sets
-   Other jewellery pieces

## 6.1 Fidelity considerations by category

Different jewellery types create different image-preservation
challenges.

-   **Rings:** Ring geometry, stone count, stone placement, prongs,
    shank shape, and proportions.
-   **Earrings:** Pair consistency, hooks or posts, symmetry, stone
    layout, and back details.
-   **Necklaces:** Chain pattern, clasp, pendant geometry, length, and
    arrangement.
-   **Pendants:** Outline, bail, stone setting, engraving, and
    attachment details.
-   **Bracelets and bangles:** Shape, closure, pattern, links, and
    repeated elements.
-   **Chains:** Link pattern, thickness, clasp, and length
    representation.
-   **Anklets:** Chain pattern, charms, closures, and proportions.
-   **Sets:** Consistency across matching items and preservation of each
    component.

Supporting every category in the product scope does not imply every
category will achieve the same quality at launch. The team must test
categories separately and document known limitations.

------------------------------------------------------------------------

# 7. Image Types and Release Boundaries

## 7.1 Included in Version 1

### Catalogue photography

Product-focused images with clean backgrounds, controlled lighting,
clear details, and consistent framing.

### Marketplace-ready photography

Images prepared for supported sales-channel requirements, including
verified framing, aspect ratio, file format, and background rules where
applicable.

Marketplace presets must be based on verified requirements. The product
must not imply that an image is compliant with every marketplace by
default.

## 7.2 Deferred to later releases

### Luxury studio photography

More dramatic lighting, premium campaign backgrounds, and
higher-art-direction compositions.

### Lifestyle and model-worn photography

Images showing jewellery on a person or within a styled real-world
context. This may require reconstructing hidden product areas or
changing perspective and is therefore more challenging under
strict-fidelity requirements.

## 7.3 Why the initial scope is narrow

Catalogue and marketplace images are the most direct way to validate the
core promise: change the presentation while preserving the actual item.
More complex scenes should be added only when fidelity can be evaluated
and maintained.

------------------------------------------------------------------------

# 8. Core User Journey

1.  User opens the mobile app.
2.  User registers or signs in.
3.  Guided onboarding introduces photo capture, image generation,
    credits, review, and downloads.
4.  User captures a photo or selects an existing phone photo.
5.  The app checks whether the image is usable and provides helpful
    capture guidance.
6.  User creates a product record or selects an existing catalogue
    product.
7.  User selects the jewellery category.
8.  User selects catalogue or marketplace output.
9.  User selects a visual preset and aspect ratio or verified
    marketplace preset.
10. The app displays the credit cost.
11. User confirms generation.
12. The app generates one image.
13. User compares the generated image side by side with the source.
14. User accepts it, reports a product-detail issue, reports a
    visual-quality issue, or requests another image.
15. A further generated image consumes additional credits, with the
    price disclosed before the request.
16. The user saves the result to the product's history.
17. User downloads the image or shares it using native phone sharing
    options.
18. The user can return later to the product and its saved images.

------------------------------------------------------------------------

# 9. Functional Requirements

## 9.1 Accounts and onboarding

### Requirements

-   Registration and sign-in are required.
-   Accounts hold the user's credit balance, products, and image
    history.
-   Guided onboarding is included.
-   A first-generation walkthrough explains the core workflow.
-   English and Hindi are included in Version 1.
-   Photo-taking guidance must be simple and actionable.
-   The app must explain image storage and deletion.
-   Credit charges must be understandable before a generation is
    started.

### Acceptance criteria

-   A new user can complete onboarding and reach the photo upload flow.
-   Essential onboarding and error messages are available in English and
    Hindi.
-   A user can return to the app and access their own saved products and
    images.
-   Users cannot view another user's products or images.

## 9.2 Photo input

### Requirements

-   Capture or upload a photo using the phone.
-   One photo is required to start.
-   Additional angles are optional.
-   Provide guidance for blurry, dark, cropped, occluded, or unsuitable
    images.
-   Avoid requiring professional equipment or studio-quality photos.
-   Explain when a hidden detail cannot be inferred from the provided
    image.

### Suggested phone-photo tips

-   Clean the camera lens.
-   Use bright, diffused light.
-   Keep the entire piece in frame.
-   Avoid strong glare and harsh shadows.
-   Keep the camera steady.
-   Use a simple, contrasting surface where possible.
-   Avoid excessive digital zoom.
-   Add another angle if a defining detail is not visible.

### Acceptance criteria

-   Users can select or capture a source photo.
-   The app can explain common image-quality problems in understandable
    language.
-   Users can proceed with a single photo when it is usable.
-   Additional angles are optional rather than mandatory.

## 9.3 Product catalogue management

Catalogue management is included from day one.

### Required capabilities

-   Create a product record.
-   Name a product.
-   Assign a jewellery category.
-   Associate source photos with the product.
-   Associate generated images with the product.
-   Browse and open saved products.
-   Revisit a product's image history.
-   Rename a product.
-   Delete a product.
-   Delete individual saved images.

### Proposed minimum product fields

Required: - Product name - Jewellery category

Potential optional fields to validate: - SKU or internal product code -
Material or metal type - Stone type - Collection name - Notes -
Reference label

Do not require a large set of product metadata until customer research
demonstrates that it is needed.

### Acceptance criteria

-   A user can create, rename, open, and delete a product.
-   A product can contain its source photo and multiple generated
    images.
-   Saved images can be revisited and downloaded.
-   Deletion behaviour is explained and consistently applied.

## 9.4 Image generation

### Requirements

-   Support catalogue and marketplace-ready outputs.
-   Provide a curated set of presets for background, lighting, and
    framing.
-   Allow aspect-ratio selection.
-   Allow verified marketplace presets where requirements are confirmed.
-   Generate one image by default.
-   Allow optional additional variations.
-   Show credit cost before each generation.
-   Preserve the jewellery's defining characteristics as a strict
    product requirement.
-   Avoid unrestricted custom prompts that can redesign the item.

### Acceptance criteria

-   The user can choose an in-scope output and preset.
-   The credit cost is visible before generation.
-   One image is generated after confirmation.
-   Additional images require a separate user action and show their
    cost.
-   The result is saved to the appropriate product history when
    retained.
-   Failures provide a clear message and follow the credit policy.

## 9.5 Image review and quality reporting

### Requirements

-   Display original and generated images side by side.
-   Allow users to accept the image.
-   Allow users to report product-detail errors.
-   Allow users to report general visual-quality issues.
-   Allow users to request another generation.
-   Explain that the user should verify the image before using it to
    sell the product.

### Suggested product-detail error categories

-   Stone count or placement changed
-   Stone shape or colour changed
-   Prongs, bezel, or setting changed
-   Metal colour or finish changed
-   Chain links or clasp changed
-   Shape or proportions changed
-   Engraving, logo, or identifying mark changed
-   Other product detail changed

### Suggested visual-quality error categories

-   Blurry or low detail
-   Poor crop or framing
-   Unnatural shadow or reflection
-   Background artefact
-   Unwanted object or visual defect
-   Other quality issue

### Acceptance criteria

-   The user can compare source and output without losing access to
    either.
-   A fidelity issue can be reported with a category.
-   The product records the report for quality analysis.
-   The user can regenerate according to the credit policy.
-   The product does not claim that automated checks guarantee exact
    fidelity.

## 9.6 Export, download, and sharing

### Requirements

-   Support multiple aspect ratios.
-   Provide downloadable images for common commerce workflows.
-   Provide a limited set of verified marketplace export presets.
-   Allow download to the phone.
-   Allow sharing through native phone sharing options.
-   Preserve access to saved images through product history.

### Unresolved export details

-   Exact aspect ratios
-   Pixel dimensions
-   File types
-   Maximum file size
-   Resolution tiers
-   Initial marketplace list
-   Per-marketplace background, crop, and image-count requirements

### Acceptance criteria

-   Each supported export preset produces an output matching its
    documented specification.
-   The app only labels a preset as marketplace-specific when
    requirements have been verified.
-   A user can download and share a saved image.
-   Export failure does not silently remove the saved image.

## 9.7 Credits and payments

### Agreed business model

-   Free trial followed by paid credit packs.
-   Each additional generated image consumes credits.
-   Credit cost is shown before generation.
-   Technical generation failures automatically return credits.
-   Users reporting incorrect jewellery details receive a credit refund
    under the quality-failure policy.

### Requirements

-   Display credit balance.
-   Show generation cost before confirmation.
-   Show a clear success or failure state.
-   Record credit transactions.
-   Return credits for technical failures automatically.
-   Provide the agreed refund path for reported fidelity failures.
-   Keep pricing understandable for the intended Indian customer base.

### Decisions still required

-   Free trial allowance
-   Credit pack sizes
-   Rupee price points
-   Cost per initial image
-   Cost per additional variation
-   Credit expiry rules
-   Payment methods
-   Receipts and purchase history
-   Handling of interrupted requests
-   Whether a fidelity refund is automatic or follows a lightweight
    report/review step
-   Safeguards for duplicate or abusive claims

## 9.8 Image history and privacy

### Agreed storage direction

Saved images remain in the user's history until the user deletes them.

### Requirements

-   Keep generated images associated with the user's account and
    product.
-   Allow users to revisit and download saved outputs.
-   Allow deletion of saved images and product records.
-   Explain how original photos, generated images, and stored copies are
    handled.
-   Protect access to user content.
-   Define how deletion requests affect originals, outputs, caches,
    backups, and any external processing copies.
-   Avoid using customer images for model training without an explicit,
    appropriate policy and permission.

### Acceptance criteria

-   A user can view only their own content.
-   Users can delete saved images and products through a clear workflow.
-   The product explains retention and deletion in understandable
    language.
-   Deletion behaviour is tested rather than assumed from removing a
    gallery thumbnail.

------------------------------------------------------------------------

# 10. Product Fidelity: Definition and Evaluation

Strict product fidelity is the defining requirement of Jewellery Image
Studio.

## 10.1 Details to preserve

-   Overall silhouette
-   Proportions and geometry
-   Number of visible stones
-   Stone shape, colour, and placement
-   Prongs, bezels, and setting structures
-   Chain pattern, links, and clasp
-   Pendant geometry and attachment
-   Metal colour and finish
-   Engravings, logos, and identifying marks
-   Distinctive features visible in the source photo

## 10.2 Allowed presentation changes

Subject to the selected preset: - Background replacement - Lighting
improvement - Framing and cropping - Aspect ratio changes that do not
cut off required product details - Presentation improvements that do not
intentionally redesign the jewellery

## 10.3 Disallowed or unacceptable changes

-   Adding or removing stones
-   Changing the number or placement of stones
-   Replacing one setting style with another
-   Changing the silhouette or proportions
-   Inventing a clasp, chain, engraving, or decorative detail
-   Altering the metal type or distinctive finish in a misleading way
-   Creating hidden details that are not supported by the source
-   Substituting a similar but different jewellery item

## 10.4 Limits of a single source photo

A single photo cannot reliably reveal all sides or hidden details of a
physical object. Optional additional angles may help, but they do not
guarantee exact reconstruction.

When a detail is not visible, the app should avoid implying that it has
verified that detail. The team should decide whether some low-quality or
ambiguous inputs need to be rejected or routed to a conservative output
mode.

## 10.5 Fidelity test design

Create a documented test set containing: - Multiple jewellery
categories - Different materials and finishes - Simple and intricate
designs - Reflective metals - Transparent, faceted, and opaque stones -
Fine chains and small details - Different phone-photo lighting
conditions - Blurry, dark, and occluded photos - Single-view and
multi-angle examples

For each test item, record: - Source image(s) - Category and material
labels where known - Expected defining details - Generated output -
Whether the output is visually usable - Whether a product detail
changed - Type and severity of the change - Generation time and cost,
once measurable - Reviewer decision and notes

## 10.6 Fidelity severity

A proposed severity framework for testing:

-   **Critical:** The output depicts a materially different item, such
    as changed stone count, major setting change, altered silhouette, or
    invented defining component.
-   **Major:** A visible defining feature changes enough to misrepresent
    the product.
-   **Minor:** A small visual discrepancy that does not appear to change
    the item's identity, but may still require review.
-   **Presentation-only:** Background, lighting, or framing differs
    without an observed product-detail change.

The final threshold for acceptable minor differences remains an
unresolved decision. Critical and major changes should not be treated as
successful outputs.

## 10.7 Launch quality gate

Before launch, define: - Number of test items and test generations -
Category and material coverage - Reviewer procedure - Critical/major
error thresholds - Minimum visual-quality criteria - Maximum acceptable
failure rate - A repeatable process for reviewing regressions after
changes

Do not claim perfect preservation based solely on a small number of
attractive sample images.

------------------------------------------------------------------------

# 11. Image Reference and Dataset Plan

The founder intends to provide multiple images. These can be used to
understand desired output quality, create a test set, compare workflows,
and assess whether model training is necessary.

**Important:** Providing images for evaluation does not automatically
train a dedicated model. A custom training effort is a separate decision
that depends on the available data, usage rights, paired examples, and
evidence that training is necessary.

## 11.1 Most useful image groups

### Group A --- Original phone photos

Unedited photos of actual jewellery, including ordinary lighting and
simple backgrounds. These represent likely customer inputs.

### Group B --- Desired final images

Professional images that demonstrate the desired catalogue quality,
framing, lighting, background, and presentation.

### Group C --- Paired original/final examples

The most useful examples are an original photo and a professional final
image of the **same physical jewellery item**. These help define the
target transformation.

### Group D --- Multiple angles of the same item

Front, side, back, and detail views where available. These help evaluate
whether additional views improve fidelity.

### Group E --- Different categories and materials

Examples across rings, earrings, necklaces, bangles, chains, gemstones,
pearls, and other relevant products.

### Group F --- Difficult cases

Reflective metals, small stones, fine chains, dark images, glare,
overlapping components, occlusions, and intricate settings.

## 11.2 Initial evaluation set

A practical starting point is 10--20 original jewellery photos, with
paired target images where available. This is a small evaluation set,
not necessarily enough data to train a model.

Start by documenting what each image demonstrates. Do not assume every
reference image is a training example or that a visually similar image
depicts the same physical item.

## 11.3 Dataset record template

For each item, record:

-   Example ID
-   Physical item ID, if known
-   Jewellery category
-   Material or metal, if known
-   Stone type, if known
-   Original phone photo path or file name
-   Additional angle file names
-   Target/reference image file name
-   Whether the target is of the same physical item
-   Visible details that must remain unchanged
-   Desired background and lighting
-   Intended use: catalogue or marketplace
-   Image rights/permission status
-   Whether the image contains customer or confidential information
-   Reviewer notes
-   Known source-image limitations

Avoid including personal data that is not needed for product evaluation.

## 11.4 Data rights and privacy

Before using any image beyond direct review: - Confirm that the uploader
has the right to share it. - Distinguish the user's own product photos
from reference images found elsewhere. - Do not assume public
availability means permission to train on an image. - Keep customer
product images private by default. - Define retention and deletion
practices. - Obtain appropriate permission before using customer images
for model training or other secondary purposes. - Track whether images
may be used for evaluation, product demos, or training separately.

## 11.5 When training should be considered

Investigate specialised training only if: 1. A baseline workflow has
been tested. 2. Fidelity failures are measured and understood. 3. The
failures are not adequately addressed by better input guidance,
conservative editing, or workflow changes. 4. There are enough suitable
examples with appropriate rights. 5. The likely quality improvement
justifies the cost and operational burden. 6. The resulting system can
be evaluated on examples that were not used to develop it.

Keep training examples separate from held-out evaluation examples.
Otherwise, test results may overstate real-world quality.

------------------------------------------------------------------------

# 12. Business Model and Credit Policies

## 12.1 Agreed model

Free trial followed by paid credit packs.

## 12.2 Core charging rules

-   Show the credit cost before the user confirms generation.
-   The initial generated image consumes credits according to the
    disclosed rule.
-   Every additional generated image consumes credits.
-   Technical generation failures automatically return credits.
-   Reported incorrect jewellery details qualify for credit refunds
    under the agreed policy.

## 12.3 Quality failure versus technical failure

A technical failure means the requested generation did not complete
successfully or produced no usable output due to a system/process error.

A quality failure means an output was generated, but the user reports
that it incorrectly changes a defining jewellery detail.

The final workflow for quality-failure refunds still needs to be
specified. It should be easy for legitimate customers to report errors,
transparent about the result, and resistant to repeated duplicate
claims.

## 12.4 Pricing decisions to validate

-   Number of free trial credits
-   Credit pack options
-   Price per pack in INR
-   Credits per standard generation
-   Credits per additional variation
-   Whether marketplace presets have different costs
-   Whether high-resolution output has a different price
-   Credit expiry or non-expiry
-   Refund timing and transaction history
-   Payment failure and interrupted generation handling

Prices should be tested against actual generation cost and willingness
to pay. Do not set prices from competitor comparisons alone.

------------------------------------------------------------------------

# 13. Marketplace and Export Requirements

Version 1 includes multiple aspect ratios and verified
marketplace-specific export presets.

## 13.1 General export needs

-   Product image should be framed appropriately.
-   The complete jewellery item should remain visible unless a
    documented crop is intended.
-   The output should have sufficient detail for the declared use.
-   The file should be downloadable to the phone.
-   The user should be able to share the file using native sharing
    options.
-   Saved outputs should remain accessible through product history.

## 13.2 Marketplace presets

For each supported marketplace, maintain a verified specification
with: - Marketplace name - Intended listing or image slot - Required and
recommended dimensions - Aspect ratio - Supported file formats - Maximum
file size, if applicable - Background requirements - Product visibility
and crop rules - Any other relevant restrictions - Source and date of
verification

Do not mark a preset as verified until the requirements have been
checked. Marketplace requirements can change, so a maintenance process
will eventually be needed.

## 13.3 Unresolved decisions

-   Which marketplaces to support first
-   Which export formats to support
-   Exact pixel dimensions and ratios
-   Whether users can select a custom ratio
-   Whether transparent backgrounds are needed
-   Whether exports need watermarks or never include them
-   Whether multiple export versions are saved as separate history items

------------------------------------------------------------------------

# 14. Privacy, Security, and User Trust

Jewellery photos may reveal valuable stock, unreleased designs, or
commercially sensitive products.

## Requirements

-   Users can access only their own products and images.
-   The app explains how images are stored and deleted.
-   Users can delete source photos, generated images, and product
    records.
-   The product defines how deletion affects copies, caches, backups,
    and external processing.
-   Images are not reused for training without an explicit and
    appropriate policy and permission.
-   Error reports should not expose private product images to other
    users.
-   Any support access to user images should be limited and governed by
    a clear policy.
-   The app should avoid overstating confidentiality or security
    guarantees.

## Decisions to resolve

-   Exact deletion timing
-   Backup retention
-   Whether original photos and generated images have different
    retention rules
-   Account deletion behaviour
-   How images are handled by any external service used for processing
-   Whether users can opt into sharing examples to improve quality

------------------------------------------------------------------------

# 15. Language and Onboarding

## Agreed languages

-   English
-   Hindi

## Onboarding requirements

-   Explain the value of the tool.
-   Show how to capture or upload a photo.
-   Explain that one photo is required and additional angles are
    optional.
-   Explain how to choose a style and generate an image.
-   Demonstrate original/result comparison.
-   Explain credits before the first charge.
-   Explain how to download and share an output.
-   Explain saved image history and deletion.

The first-generation walkthrough should be brief and practical. It
should not force experienced users to repeat a long tutorial every time
they use the app.

------------------------------------------------------------------------

# 16. Metrics and Validation

## 16.1 Product usage metrics

-   Account creation to first upload
-   Upload-to-generation conversion
-   Time to first result
-   Accepted-image rate
-   Download rate
-   Share rate
-   Repeat generation rate
-   Number of products and images saved per active user
-   Repeat use of saved product records

## 16.2 Quality metrics

-   Product-detail complaint rate
-   Critical and major fidelity error rate
-   General visual-quality complaint rate
-   Technical generation failure rate
-   Quality refund rate
-   Percentage of outputs users consider commercially usable
-   Quality by category, material, input-photo condition, and preset

## 16.3 Business metrics

-   Free trial activation
-   Trial-to-credit-purchase conversion
-   Credit pack purchase rate
-   Repeat credit purchase
-   Revenue per paying account
-   Cost per generated image
-   Cost per accepted image
-   Support cost per active customer

## 16.4 Validation plan

### Phase 1 --- Customer discovery

-   Interview sellers across the included segments.
-   Understand current photography workflow, costs, delays, and channel
    requirements.
-   Test whether the proposed output quality would be useful.
-   Investigate willingness to pay for an accepted image.

### Phase 2 --- Reference image review

-   Collect original phone photos and desired final examples.
-   Label category, visible product details, target use, and
    permissions.
-   Identify the most challenging fidelity cases.

### Phase 3 --- Baseline quality evaluation

-   Test a conservative catalogue workflow.
-   Compare results with originals.
-   Record visual usability and product-detail errors separately.
-   Measure time and cost once a workflow is selected.

### Phase 4 --- Mobile workflow validation

-   Test upload, product creation, preset selection, generation, review,
    reporting, and export.
-   Observe whether users understand the credit system.
-   Test with actual jewellers using their own phone photos.

### Phase 5 --- Paid pilot

-   Offer the agreed trial and credit packs to a small user cohort.
-   Track accepted images, refunds, repeat usage, and cost per accepted
    image.
-   Expand only when quality and economics are sustainable.

------------------------------------------------------------------------

# 17. Explicitly Out of Scope for Version 1

-   Luxury campaign photography
-   Lifestyle and model-worn photography
-   Video or animation generation
-   Bulk image generation
-   Bulk catalogue imports
-   Direct publishing to marketplaces
-   Direct publishing to social platforms
-   Advanced manual editing
-   Unrestricted custom prompts
-   Team workspaces and shared approval workflows
-   Advanced catalogue analytics
-   Guaranteed automated detection of all product changes
-   Additional interface languages beyond English and Hindi
-   Subscription plans as a launch requirement
-   Enterprise-specific workflows

These are future possibilities, not Version 1 commitments.

------------------------------------------------------------------------

# 18. Remaining Unresolved Decisions

## Highest priority

1.  Which customer segment should be prioritised for the first pilot,
    even though all segments remain in scope?
2.  Which marketplaces should have verified presets at launch?
3.  What exact aspect ratios, pixel dimensions, file types, and size
    limits are required?
4.  What fidelity test size and acceptable error thresholds define
    launch readiness?
5.  How should a reported fidelity issue trigger a refund?
6.  What are the free trial allowance, credit pack sizes, INR prices,
    and credit cost per image?
7.  Which product fields are required beyond name and category?

## Before launch

8.  Which mobile operating systems and minimum versions must be
    supported?
9.  What payment methods and receipts are required?
10. What are the exact retention and deletion rules for originals,
    outputs, and backups?
11. What account recovery and account deletion workflows are required?
12. What is the support process for quality complaints?
13. What happens if a generation is interrupted by a network failure?
14. What export formats and resolution tiers will be offered?
15. Can users use custom aspect ratios or only predefined choices?

## Later validation

16. Whether additional style preferences are needed
17. Whether product collections beyond basic catalogue management are
    needed
18. Whether bulk generation is commercially important
19. Whether more Indian languages are needed
20. Whether subscriptions make sense for frequent users
21. Whether automated quality checks materially improve user trust

------------------------------------------------------------------------

# 19. Launch Acceptance Checklist

Version 1 should not be considered launch-ready until the team can
verify the following.

## Accounts and onboarding

-   [ ] Users can register and sign in.
-   [ ] Guided onboarding is available in English and Hindi.
-   [ ] Users understand photo input, generation, credits, review, and
    deletion.

## Input and catalogue

-   [ ] Users can capture or upload one phone photo.
-   [ ] Additional angles are optional.
-   [ ] Users receive helpful guidance for unsuitable photos.
-   [ ] Users can create, name, browse, rename, and delete product
    records.
-   [ ] Source photos and generated images are associated with the
    correct product.

## Generation and review

-   [ ] Users can choose catalogue or marketplace output.
-   [ ] Users can choose a supported preset.
-   [ ] Credit costs are visible before generation.
-   [ ] One image is generated initially.
-   [ ] Additional variations are optional and charged separately.
-   [ ] Original and generated images can be compared side by side.
-   [ ] Users can report fidelity and visual-quality issues.
-   [ ] The quality workflow does not claim guaranteed accuracy.

## Credits and refunds

-   [ ] Technical failures automatically return credits.
-   [ ] Reported incorrect jewellery details follow the agreed refund
    policy.
-   [ ] Credit balances and transactions are understandable.
-   [ ] Failed or interrupted requests do not create duplicate charges.

## Export and history

-   [ ] Supported aspect ratios work as specified.
-   [ ] Marketplace presets are verified and documented.
-   [ ] Users can download and share images.
-   [ ] Saved images can be revisited from product history.

## Privacy and fidelity

-   [ ] Users can access only their own content.
-   [ ] Deletion behaviour is documented and tested.
-   [ ] Retention rules cover source and generated images.
-   [ ] The fidelity evaluation set has been reviewed.
-   [ ] Critical and major product-detail errors meet the agreed
    threshold.
-   [ ] Quality has been evaluated across categories and source-photo
    conditions.

## Business readiness

-   [ ] Trial credits and paid packs are defined.
-   [ ] INR pricing is visible before purchase.
-   [ ] Payment and receipt flows are tested.
-   [ ] Support and refund policies are published.
-   [ ] Cost per accepted image is measured.

------------------------------------------------------------------------

# 20. Recommended Immediate Next Steps

1.  Gather 10--20 original jewellery phone photos, ideally with paired
    professional images of the same physical items.
2.  Label each example with its category, visible defining details,
    intended output, and usage permissions.
3.  Use the examples to define the initial fidelity test set; do not
    assume they automatically constitute training data.
4.  Choose the first marketplaces and verify their image requirements.
5.  Define the minimum product fields for catalogue management.
6.  Establish quality acceptance criteria and the refund workflow.
7.  Validate trial-credit and credit-pack economics.
8.  Only after product requirements and evaluation criteria are clear,
    compare implementation approaches and decide whether a specialised
    model or training is necessary.

## Final product definition

Jewellery Image Studio Version 1 is a mobile app for Indian jewellery
sellers that combines phone-photo input, catalogue and marketplace image
generation, strict product-fidelity review, product catalogue
management, saved image history, downloadable exports, English/Hindi
onboarding, and a credit-based business model.

The product's success should be judged by whether sellers can repeatedly
create commercially useful images of their actual jewellery at an
acceptable cost---not by the number of AI features or the visual
attractiveness of outputs that misrepresent the item.
