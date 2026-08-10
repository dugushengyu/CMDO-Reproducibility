function tests = test_pair_complete_observer
tests = functiontests(localfunctions);
end

function testAUCVariance(testCase)
[auc, variance] = cmdo.auc_and_variance([0.9;0.8], [0.2;0.1]);
verifyEqual(testCase, auc, 1, 'AbsTol', 1e-14);
verifyGreaterThanOrEqual(testCase, variance, 0);
end

function testExactFallbackIdentity(testCase)
positive = linspace(0.55,0.95,20)';
negative = linspace(0.05,0.45,20)';
result = cmdo.pair_complete_observer(positive, negative, 0.6, 0, 0.1, 1, 'Seed', 7);
verifyLessThan(testCase, result.identity_residual, 1e-14);
verifyEqual(testCase, result.mean_weight, 0, 'AbsTol', 1e-14);
verifyEqual(testCase, result.estimate, result.direct_full_auc, 'AbsTol', 1e-14);
end

function testDeterministicSeed(testCase)
positive = (1:20)'/20;
negative = (0:19)'/25;
a = cmdo.pair_complete_observer(positive,negative,0.7,0.8,0.02,0.75,'Seed',33);
b = cmdo.pair_complete_observer(positive,negative,0.7,0.8,0.02,0.75,'Seed',33);
verifyEqual(testCase, a.estimate, b.estimate, 'AbsTol', 1e-14);
verifyEqual(testCase, a.mean_weight, b.mean_weight, 'AbsTol', 1e-14);
end
