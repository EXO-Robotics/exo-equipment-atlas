# Private research inputs

`research/private/` is intentionally ignored by Git. It may contain locally
acquired manufacturer publications used for evidence review. Do not move these
files into tracked folders.

The tracked source manifests contain the expected local path, byte count, page
count, and SHA-256. Run `npm run check:sources` to verify the local evidence
freeze without publishing the source documents.
