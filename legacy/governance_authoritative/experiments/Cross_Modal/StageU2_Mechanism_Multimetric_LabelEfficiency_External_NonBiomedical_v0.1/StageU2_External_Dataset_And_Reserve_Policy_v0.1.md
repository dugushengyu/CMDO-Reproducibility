# Stage U2 — External Dataset Acquisition and Reserve Policy v0.1

## Developmental external validation used now
### CIFAR-10
Purpose: source training and clean reference.
Acquisition: automatic through torchvision.

### CIFAR-10.1 v6
Purpose: independently collected natural test-set replication.
Acquisition: automatic official-repository download, with TensorFlow Datasets fallback.

### CIFAR-10-C
Purpose: broad non-biomedical corruption environments.
Selected families:
gaussian noise, shot noise, impulse noise, Gaussian blur, motion blur, fog, frost, brightness, contrast, JPEG compression, pixelation, and zoom blur.

Selected severities:
1, 3, and 5.

Acquisition: automatic through TensorFlow Datasets, with persistent Google Drive caching.

## Untouched reserve
### DomainNet cleaned
Candidate domains:
clipart, quickdraw, sketch, and painting.

DomainNet is not downloaded or inspected in Stage U2. This preserves it for final outcome-free roster selection, hash freezing, and prospective law prediction.

## Manual intervention rule
No manual action is expected for Stage U2. Manual acquisition is allowed only after an automatic download error is recorded, and only for the exact public file that failed. The reserve must not be opened as a workaround.

