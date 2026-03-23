let firstLoad = true;
document$.subscribe(() => {
  if (firstLoad) {
    firstLoad = false;
    return;
  }
  MathJax.typesetClear();
  MathJax.typesetPromise();
})
