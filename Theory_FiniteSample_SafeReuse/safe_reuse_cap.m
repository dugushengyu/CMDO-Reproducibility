function omega = safe_reuse_cap(B, V)
%SAFE_REUSE_CAP Oracle hard cap for role-separated finite-sample reuse.
%
%   omega = SAFE_REUSE_CAP(B,V) returns
%
%       min(1, 2/(1 + B^2/V))
%
%   for scalar or array-compatible B and V.
%
%   Assumptions for the corresponding no-harm sufficient condition:
%     1) D is unbiased for theta with finite-sample variance V > 0;
%     2) H is fixed after completion with B = H-theta;
%     3) adaptive W is independent of D and satisfies 0 <= W <= omega.
%
%   This helper is ORACLE / post-completion because B contains target truth.
%   It is not a deployment-time gate.

    if any(V(:) <= 0 | ~isfinite(V(:)))
        error('safe_reuse_cap:InvalidVariance', ...
            'V must be finite and strictly positive.');
    end
    if any(~isfinite(B(:)))
        error('safe_reuse_cap:InvalidBias', ...
            'B must be finite.');
    end

    lambda = (B.^2) ./ V;
    omega = min(1, 2 ./ (1 + lambda));
end
