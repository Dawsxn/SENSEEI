/** The reading, shown as the instructor's original PDF.
 *
 * The student reads the document as it was uploaded, figures and tables
 * included; the extracted text behind it is what the agents grade against. That
 * makes this the one place a figure a student cites is actually visible.
 *
 * Pages render continuously rather than one at a time. A reading is read start
 * to finish, so scrolling is the natural motion and the page counter follows
 * the scroll instead of driving it.
 *
 * Sized to fit the pane's width, which is why there are no zoom controls: the
 * percentage is a readout of that fit, as in the mockup. Below `lg` the pane
 * toggle already gives the PDF the full viewport.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";

import "react-pdf/dist/Page/TextLayer.css";

// Bundled by Vite from the installed package rather than fetched from a CDN, so
// the viewer keeps working offline and cannot drift from the pdfjs version the
// app was built against.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

// Module-level so the identity is stable: a fresh object each render would make
// react-pdf tear the document down and refetch it on every state change.
const PDF_OPTIONS = { withCredentials: true };

/** Horizontal padding around the page stack, matching the mockup's 24px. */
const GUTTER = 24;
/** Space above the first page. Also how far a page jump backs off, so a jumped-to
 *  page sits exactly where the first one does rather than flush to the edge. */
const PAGE_GAP = 20;
/** Above this the page stops growing. It should read as a document, not a wall. */
const MAX_PAGE_WIDTH = 900;

interface PdfPanelProps {
  fileUrl: string;
  /** Shown if the document cannot be loaded — the extracted text, so a broken
   *  PDF costs the student nothing. */
  fallback: React.ReactNode;
}

export function PdfPanel({ fileUrl, fallback }: PdfPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<(HTMLDivElement | null)[]>([]);

  const [numPages, setNumPages] = useState(0);
  const [naturalWidth, setNaturalWidth] = useState(0);
  const [pageWidth, setPageWidth] = useState(0);
  const [current, setCurrent] = useState(1);
  const [failed, setFailed] = useState(false);

  // Fit to the pane. A ResizeObserver rather than a window listener, because the
  // pane also changes width when the layout switches at the `lg` breakpoint.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const measure = () => {
      const available = el.clientWidth - GUTTER * 2;
      setPageWidth(Math.max(0, Math.min(available, MAX_PAGE_WIDTH)));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const onLoad = useCallback(async (pdf: pdfjs.PDFDocumentProxy) => {
    setNumPages(pdf.numPages);
    const page = await pdf.getPage(1);
    setNaturalWidth(page.getViewport({ scale: 1 }).width);
  }, []);

  // The counter follows the scroll: the current page is the last one whose top
  // has passed the top of the viewport.
  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const line = el.scrollTop + 80;
    let page = 1;
    pageRefs.current.forEach((node, i) => {
      if (node && node.offsetTop <= line) page = i + 1;
    });
    setCurrent(page);
  }, []);

  // Jumps instantly rather than smoothly. A smooth scroll here is animated over
  // a whole page height and gets cancelled partway whenever a page canvas
  // finishes rendering and resizes the stack under it, leaving the reader
  // stranded between pages. A page control should land on the page.
  const goToPage = useCallback((n: number) => {
    const node = pageRefs.current[n - 1];
    const el = scrollRef.current;
    if (!node || !el) return;
    el.scrollTop = node.offsetTop - PAGE_GAP;
  }, []);

  const zoom = useMemo(
    () =>
      naturalWidth && pageWidth ? Math.round((pageWidth / naturalWidth) * 100) : null,
    [naturalWidth, pageWidth],
  );

  if (failed) {
    return (
      <div className="flex h-full flex-col">
        <p className="shrink-0 border-b bg-[#fffbeb] px-4 py-2 text-[13px] text-[#92400e]">
          Couldn&rsquo;t display the PDF. Showing the reading&rsquo;s text instead.
        </p>
        <div className="min-h-0 flex-1">{fallback}</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <Toolbar
        current={current}
        numPages={numPages}
        zoom={zoom}
        fileUrl={fileUrl}
        onPrev={() => goToPage(Math.max(1, current - 1))}
        onNext={() => goToPage(Math.min(numPages, current + 1))}
      />

      {/* `relative` is load-bearing: it makes this the offsetParent of the page
          stack, so a page's offsetTop is measured from the top of the scroll
          area. Without it the offsets are document-relative and include the
          chrome above, which throws off both the counter and the page jump. */}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="relative min-h-0 flex-1 overflow-y-auto bg-[#e9e9ec]"
      >
        <div
          className="flex flex-col items-center pb-7"
          style={{ paddingLeft: GUTTER, paddingRight: GUTTER, paddingTop: PAGE_GAP }}
        >
          <Document
            file={fileUrl}
            options={PDF_OPTIONS}
            onLoadSuccess={onLoad}
            onLoadError={() => setFailed(true)}
            loading={<Notice>Loading the reading&hellip;</Notice>}
            error={<Notice>Couldn&rsquo;t display the PDF.</Notice>}
            className="flex flex-col items-center gap-4"
          >
            {/* Nothing renders until the fitted width is known. Rendering at the
                natural width first and re-rendering once the observer reports
                would rasterise every page twice, which on a long reading is the
                difference between a pane that appears and one that hangs. */}
            {(pageWidth ? Array.from({ length: numPages }, (_, i) => i) : []).map((i) => (
              <div
                key={i}
                ref={(node) => {
                  pageRefs.current[i] = node;
                }}
                className="bg-white shadow-[0_1px_3px_rgba(0,0,0,0.14)]"
              >
                <Page
                  pageNumber={i + 1}
                  width={pageWidth}
                  renderTextLayer
                  renderAnnotationLayer={false}
                />
              </div>
            ))}
          </Document>
        </div>
      </div>
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="px-4 py-10 text-[13px] text-muted-foreground">{children}</p>;
}

interface ToolbarProps {
  current: number;
  numPages: number;
  zoom: number | null;
  fileUrl: string;
  onPrev: () => void;
  onNext: () => void;
}

function Toolbar({ current, numPages, zoom, fileUrl, onPrev, onNext }: ToolbarProps) {
  return (
    <div className="flex h-10 shrink-0 items-center justify-between border-b bg-white px-3">
      <div className="flex items-center gap-1.5">
        <IconButton label="Previous page" onClick={onPrev} disabled={current <= 1}>
          <ChevronLeft className="h-3.5 w-3.5" />
        </IconButton>
        <span className="text-[12px] tabular-nums text-muted-foreground">
          {numPages ? `${current} of ${numPages}` : "—"}
        </span>
        <IconButton
          label="Next page"
          onClick={onNext}
          disabled={numPages === 0 || current >= numPages}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </IconButton>
      </div>

      <div className="flex items-center gap-2.5">
        {zoom !== null && (
          <span className="text-[12px] tabular-nums text-muted-foreground">{zoom}%</span>
        )}
        <div className="h-3.5 w-px bg-border" />
        <a
          href={fileUrl}
          download
          aria-label="Download the reading"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          <Download className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40 disabled:hover:text-muted-foreground"
    >
      {children}
    </button>
  );
}
