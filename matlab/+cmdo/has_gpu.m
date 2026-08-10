function [available, info] = has_gpu(initialize)
%HAS_GPU Check for a MATLAB-compatible GPU without making it mandatory.

if nargin < 1
    initialize = false;
end
available = false;
info = struct('count', 0, 'name', '', 'computeCapability', '', ...
    'driverVersion', '', 'message', '');

if exist('gpuDeviceCount', 'file') ~= 2
    info.message = 'gpuDeviceCount is unavailable (Parallel Computing Toolbox not detected).';
    return;
end

try
    try
        count = gpuDeviceCount("available");
    catch
        count = gpuDeviceCount;
    end
    info.count = double(count);
    available = count > 0;
    if available && initialize
        device = gpuDevice();
        info.name = char(string(device.Name));
        if isprop(device, 'ComputeCapability')
            info.computeCapability = char(string(device.ComputeCapability));
        end
        if isprop(device, 'DriverVersion')
            info.driverVersion = char(string(device.DriverVersion));
        end
    elseif available
        info.message = 'Compatible GPU detected; call gpuDevice to initialize it.';
    else
        info.message = 'No MATLAB-compatible GPU is currently available.';
    end
catch ME
    available = false;
    info.message = ME.message;
end
end
