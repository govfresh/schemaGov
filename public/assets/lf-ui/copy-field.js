// Generic "copy to clipboard" button. Two ways to say what it copies:
// - a `[data-copy]` button next to an `<input readonly>`/`<textarea>` in
//   the same .input-group (a schema ID, an IRI, a namespace) — the
//   original, still-default shape;
// - `data-copy-target="<selector>"` naming any other element to read text
//   from instead (a syntax-highlighted <code> block, for example, where
//   there's no input to pair with) — checked first so it takes priority
//   when both could apply.
// Either way, only the button's .copy-label text swaps on click, not its
// full contents, so an icon placed beside the label survives the
// "Copied!" flash instead of being wiped out by it.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    var source = btn.dataset.copyTarget
      ? document.querySelector(btn.dataset.copyTarget)
      : (function () {
          var group = btn.closest('.input-group');
          return group ? group.querySelector('input, textarea') : null;
        })();
    var label = btn.querySelector('.copy-label') || btn;
    if (!source) return;

    var text = label.textContent;
    btn.addEventListener('click', function () {
      var value = 'value' in source ? source.value : source.textContent;
      navigator.clipboard.writeText(value).then(function () {
        label.textContent = 'Copied!';
        setTimeout(function () {
          label.textContent = text;
        }, 1500);
      });
    });
  });
});
