// "Export PDF" = the browser's print dialog (Save as PDF), with the print styles in
// index.css. The document title becomes the suggested file name.
export function printAsPdf(fileName) {
  const previous = document.title;
  document.title = fileName;
  const restore = () => {
    document.title = previous;
    window.removeEventListener('afterprint', restore);
  };
  window.addEventListener('afterprint', restore);
  window.print();
}
