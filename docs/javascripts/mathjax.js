window.MathJax = {
  startup: {
    typeset: false,
    ready() {
      MathJax.startup.defaultReady();
      document$.subscribe(() => {
        MathJax.typesetPromise()
      })
    }
  }
};
