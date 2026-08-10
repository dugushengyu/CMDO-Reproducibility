function root = repo_root()
%REPO_ROOT Return the absolute root of this checkout.

packageDir = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(packageDir));
end
