# Computing the variance of a data stream in one pass

Let x_1, ..., x_n be a stream of floating-point numbers.

**Textbook one-pass formula.** Accumulate S1 = sum x_i and S2 = sum x_i^2, then
report the population variance as S2/n - (S1/n)^2.

**Welford's online algorithm (1962).** Keep a running count n, mean m and sum
of squared deviations M2. For each new x: n += 1; d = x - m; m += d / n;
M2 += d * (x - m). Report the population variance as M2 / n.

**Claim.** Both are exact in real arithmetic, but in double precision the
one-pass formula suffers catastrophic cancellation when the mean is large
compared with the standard deviation: its relative error grows roughly with
(mean / standard deviation)^2, and it can even return negative variances.
Welford's update stays accurate to a few units in the last place across the
same range.
