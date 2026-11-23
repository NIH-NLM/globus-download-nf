# globus-download-nf

A Nextflow workflow that downloads everything under one or more folders of a Globus collection. It lists the folders recursively, downloads each file as its own task (so files download in parallel and a failed file is retried alone), keeps the folder structure, and checks files against any `fastq_md5sum.txt` it finds.

It reads the collection over HTTPS, so the collection needs HTTPS access turned on.

## One-time setup (each user)

A login that needs a browser or a card (such as a PIV card) cannot happen on a batch node, so you sign in once and save a long-lived token as a secret.

1. Register a free Globus "native app" at https://developers.globus.org and note its client ID.
2. In a Jupyter terminal on the platform, run the helper from this repo:

   ```bash
   pip install globus-sdk==4.10.0
   python container/globus_tools/globus_login.py --client-id YOUR_CLIENT_ID --collection COLLECTION_UUID
   ```

   Open the URL it prints, sign in with your institution, paste the code back. It prints one line of JSON.
3. Save that line as a private variable (or secret) named `GLOBUS_TOKENS`. Do not paste it anywhere else. It is a credential for your own account.
   If your platform changes quotes in parameters, save the JSON as base64 instead (macOS: `base64 -i ~/globus_tokens.json | tr -d '\n'`). The workflow accepts either.
4. On Lifebit, set the job parameter `--globus_tokens` to that variable. On a platform with Nextflow secrets, leave `--globus_tokens` unset and the secret `GLOBUS_TOKENS` is used.

A token passed as a parameter can appear in the job's run files. Keep the project private, and revoke the token at https://auth.globus.org/v2/web/consents if it leaks.

If the token expires or is revoked, run step 2 again and update the secret.

## Run

```bash
nextflow run main.nf --collection COLLECTION_UUID --paths '/' --outdir results
```

- `--collection` the collection UUID (required)
- `--paths` comma separated folders, default `/` (the whole collection), for example `--paths 'FolderA,FolderB'`
- `--outdir` default `results`
- `--globus_image` to use a different image

## What you get

- every file under `--outdir`, in the same folders as on the collection
- `md5_reports/<folder>.json` for each folder that has a `fastq_md5sum.txt`. A mismatch, a missing file or an unreadable checksum line fails the run and names the file. Downloaded data is never deleted.

## Notes

- The token is never printed in logs or written to outputs. When passed with `--globus_tokens` it can appear in the job's run files (see above).
- Uploading and Globus-to-Globus transfer are not supported.
- Tests: `pip install -r container/globus_tools/requirements.txt pytest` then `pytest container/globus_tools/tests`.
