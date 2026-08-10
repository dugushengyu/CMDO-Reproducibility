function tests = test_cmdo_core
tests = functiontests(localfunctions);
end

function testAUC(testCase)
verifyEqual(testCase, cmdo_auc([0.9;0.8], [0.2;0.1]), 1, 'AbsTol', 1e-14);
verifyEqual(testCase, cmdo_auc([0.5;0.5], [0.5;0.5]), 0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, cmdo_auc([0.1;0.2], [0.8;0.9]), 0, 'AbsTol', 1e-14);
end

function testQuantile(testCase)
verifyEqual(testCase, cmdo_quantile(1:5, 0), 1);
verifyEqual(testCase, cmdo_quantile(1:5, 0.5), 3);
verifyEqual(testCase, cmdo_quantile(1:5, 1), 5);
end

function testSpearman(testCase)
verifyEqual(testCase, cmdo_spearman((1:10)', (1:10)'), 1, 'AbsTol', 1e-14);
verifyEqual(testCase, cmdo_spearman((1:10)', (10:-1:1)'), -1, 'AbsTol', 1e-14);
end

function testSummaryValue(testCase)
T = table(["A";"B"], [0.1;0.2], 'VariableNames', {'method','gain'});
verifyEqual(testCase, cmdo_summary_value(T, 'B', 'gain'), 0.2, 'AbsTol', 1e-14);
end

function testLowessDeterminism(testCase)
x = (1:20)';
y = 2*x + sin(x);
cluster = "c" + string(ceil(x/4));
[g1,f1,l1,u1] = cmdo_lowess_bootstrap(x,y,cluster,0.4,20,17);
[g2,f2,l2,u2] = cmdo_lowess_bootstrap(x,y,cluster,0.4,20,17);
verifyEqual(testCase, g1, g2);
verifyEqual(testCase, f1, f2, 'AbsTol', 1e-12);
verifyEqual(testCase, l1, l2, 'AbsTol', 1e-12);
verifyEqual(testCase, u1, u2, 'AbsTol', 1e-12);
end
