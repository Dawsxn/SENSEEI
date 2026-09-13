import "@testing-library/jest-dom/vitest";

// jsdom implements no layout and therefore no scrolling, so elements have no
// `scrollTo`. Panes call it in an effect after mount — the chat scrolls to the
// newest message, the PDF scrolls to a page — and without this a component test
// fails on a missing browser behaviour rather than on what it set out to check.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}
