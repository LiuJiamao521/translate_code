# 随手写的 R 演示脚本，只用到基础包，方便测翻译
# 若报错先看 R 版本；这段没做兼容性兜底

set.seed(2026)

roll_dice <- function(n = 10) {
  # 有放回抽样，不是加密随机源
  sample(1:6, size = n, replace = TRUE)
}

running_sum <- function(x) {
  if (length(x) == 0) return(numeric(0))
  cumsum(x)
}

normalize01 <- function(x) {
  r <- max(x) - min(x)
  # 常数向量就全体退回 0.5，避免除零
  if (r == 0) return(rep(0.5, length(x)))
  (x - min(x)) / r
}

even_indices <- function(vec) {
  # 返回偶数下标（按位置 1,2,3…）
  which(seq_along(vec) %% 2 == 0)
}

make_dummy_frame <- function(rows = 8) {
  data.frame(
    id = seq_len(rows),
    score = round(runif(rows, min = 0, max = 100), 1),
    tag = sample(c("A", "B", "C"), rows, replace = TRUE),
    stringsAsFactors = FALSE
  )
}

summarize_by_tag <- function(df) {
  # 按 tag 聚合，求 score 的均值
  agg <- aggregate(score ~ tag, data = df, FUN = mean)
  names(agg) <- c("tag", "mean_score")
  agg[order(agg$mean_score, decreasing = TRUE), ]
}

safe_div <- function(a, b) {
  ifelse(b == 0, NA_real_, a / b)
}

clip <- function(x, lo, hi) {
  # 把值夹在 [lo, hi] 之间
  pmax(pmin(x, hi), lo)
}

first_where <- function(pred, vec) {
  idx <- which(pred(vec))
  if (length(idx) == 0) return(NA_integer_)
  idx[[1]]
}

# --- 下面跑一小段流水线 --- 
d <- roll_dice(12)
cat("dice sum:", sum(d), "\n")

x <- c(3, 1, 4, 1, 5, 9, 2, 6)
cat("norm01:", paste(round(normalize01(x), 3), collapse = ", "), "\n")

df <- make_dummy_frame(12)
print(head(df, 3))
print(summarize_by_tag(df))

z <- c(-2, 0, 7, 99, -50)
cat("clipped:", paste(clip(z, -5, 10), collapse = ", "), "\n")
cat("first >3 index:", first_where(function(v) v > 3, x), "\n")
