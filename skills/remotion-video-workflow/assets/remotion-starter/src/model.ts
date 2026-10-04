export const learningRate = 0.18;
export const loss = (theta: number) => (theta - 2) ** 2;
export const step = (theta: number) => ({
  theta, loss: loss(theta), gradient: 2 * (theta - 2),
  next: theta - learningRate * 2 * (theta - 2),
});
export const trajectory = Array.from({length: 9}, (_, i) => step(2 + 4 * (1 - 2 * learningRate) ** i));
export const stateAt = (frame: number) => {
  const position = Math.min(8, Math.max(0, frame / 20));
  const i = Math.floor(position), p = position - i;
  const a = trajectory[i], b = trajectory[Math.min(i + 1, 8)];
  return {...step(a.theta + (b.theta - a.theta) * p), iteration: i};
};
