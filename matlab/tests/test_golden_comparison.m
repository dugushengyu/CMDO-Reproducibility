function tests = test_golden_comparison
tests = functiontests(localfunctions);
end

function testNumericTolerance(testCase)
expected = table([1;2], [0.1;0.2], ["x";"y"], ...
    'VariableNames', {'id','value','label'});
actual = expected;
actual.value(2) = actual.value(2) + 1e-13;
report = cmdo.compare_golden_tables(expected, actual, {'id'}, 1e-12, false);
verifyTrue(testCase, all(report.passed));
end

function testMismatchDetected(testCase)
expected = table([1;2], ["x";"y"], 'VariableNames', {'id','label'});
actual = table([1;2], ["x";"z"], 'VariableNames', {'id','label'});
report = cmdo.compare_golden_tables(expected, actual, {'id'}, 0, false);
verifyFalse(testCase, report.passed(report.column=="label"));
end
