function label = cmdo_short_target(target)
%CMDO_SHORT_TARGET Convert canonical identifiers to compact plot labels.

label = string(target);
label = replace(label, "ACS_PUBLIC_COVERAGE_2024_", "");
label = replace(label, "ACS_INCOME_2022_", "");
label = replace(label, "MEDICAL_DERMOSCOPY_", "");
label = replace(label, "NATURAL_IMAGE_", "");
label = replace(label, "GENRE_", "Genre ");
label = replace(label, "QMNIST_TEST50K", "QMNIST");
label = replace(label, "_", " ");
label = strtrim(label);
end
