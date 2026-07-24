# Deploy to Render

## Before pushing to GitHub

1. Change the local PostgreSQL password and `SECRET_KEY` because the existing `.env` contained development credentials.
2. Confirm `.env` is not staged: `git status --ignored`.
3. Commit `.env.example`, `.gitignore`, `render.yaml`, and `init_db.py`, but never commit `.env`, `venv`, or runtime uploads.

## Deploy

1. Push the repository to GitHub.
2. In Render, choose **New** → **Blueprint** and select the repository. Render will read `render.yaml` and create the web service and PostgreSQL database.
3. Deploy. The startup command creates missing database tables without adding demo accounts or products.
4. Open `/health` on the deployed URL to confirm the service is healthy.

## Database

The Render database is separate from PostgreSQL on your computer. `DATABASE_URL` is supplied automatically by `render.yaml`.

To keep existing local products and users, export your local database with `pg_dump` and restore it into the Render database using the external connection URL shown in the Render PostgreSQL dashboard. Otherwise, start fresh and create production categories, brands, users, and products through the app/database administration process.

## Product images

The app currently writes uploaded images to its local filesystem. Render storage is ephemeral, so those uploads are not guaranteed to survive a redeploy. Use Cloudinary, Amazon S3, or another object-storage provider before relying on production product-image uploads.
