# Data retention and deletion (draft)

Spec §9.8 and §14 require explaining how photos are stored and deleted, and testing it. This is what the backend does today. Items marked **Decide** need a founder or legal decision before launch.

## What is stored

| Data | Where | Kept until |
|---|---|---|
| Source photos (as uploaded) | File storage, `products/<product>/` | The user deletes the photo, the product, or their account |
| Cut-out of each photo | Same folder | Same as its source photo |
| Generated images (background, preview, full file) | Same folder | The user deletes the image, the product, or their account |
| Product details (name, category, SKU…) | Database | The user deletes the product or their account |
| Quality reports | Database: category, note, preset and jewellery category; **no image** | Kept for quality analysis (§16.2), with no images and no phone number |
| Credit ledger and payments | Database | Kept for accounting and tax; personal details removed on account deletion |
| Phone number | Database | Removed on account deletion. A one-way hash stays in the trial-credit record so the trial can't be claimed twice |
| Sign-in codes | Database, hashed | Expire after 10 minutes |

## What deletion does (tested in `tests/test_review_refunds_deletion.py`)

- **Delete an image:** removes its files and record immediately. Its reports stay, without the image.
- **Delete a photo:** removes the photo and its cut-out. Images made from it stay; their compare view says the original was deleted.
- **Delete a product:** removes the product, all its photos and images, and the whole folder.
- **Delete an account:** does all of the above for every product, clears the phone number and name, and signs the device out.

## Not covered yet

- **Decide** backup retention, for example "backups are kept 30 days, then overwritten", and say so in the app.
- **Decide** whether originals and generated images get different retention rules (§14).
- **Check** how long each external processor (e.g. Replicate) keeps uploaded inputs and outputs, and set the shortest option available. Mention them in the privacy policy.
- **Training:** customer images are not used for training. Any future use needs an explicit opt-in (§11.4, §14).
- **Support access** to user images needs a written policy before anyone gets admin access (§14).
