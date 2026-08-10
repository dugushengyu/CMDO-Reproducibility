# GitHub storage and local GPU boundary

GitHub is the source-control and collaboration layer, not the bulk scientific-data drive.

- GitHub blocks regular Git objects larger than 100 MiB and recommends keeping repositories small.
- Git LFS is metered storage/bandwidth and every changed large-file version adds storage.
- Raw/restricted data, canonical ZIPs, weights and generated figures therefore remain on local/external storage.
- The machine-local paths are selected through `config/local_paths.json`, which is ignored by Git.

References:

- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
- https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage

A local NVIDIA GPU helps only when the called MATLAB function implements GPU execution. `RUN_ENVIRONMENT_CHECK` reports MATLAB-visible GPU availability; it does not claim that every stage is GPU accelerated. Current U8/U9 statistical pipelines are primarily CPU work. Future image/deep-learning ports should use supported GPU-enabled functions and must still pass the same golden-output gates.

Reference:

- https://www.mathworks.com/help/parallel-computing/gpu-computing-requirements.html
