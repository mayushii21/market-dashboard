window.addEventListener("load", function () {
  function checkIfInitialLoadComplete() {
    const initialLoadElement = document.getElementById("initial-load");

    // Check if the element exists and has no classes (the loading screen has finished)
    if (initialLoadElement && initialLoadElement.classList.length === 0) {
      window.dispatchEvent(new Event("resize"));
      return true; // Stop the loop
    }

    return false; // Continue checking
  }

  // Poll until #initial-load has no classes
  const intervalId = setInterval(() => {
    if (checkIfInitialLoadComplete()) {
      clearInterval(intervalId); // Stop checking once the condition is met
    }
  }, 100);

  setTimeout(() => {
    clearInterval(intervalId);
  }, 10000);
});
