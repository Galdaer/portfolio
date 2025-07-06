const vm = require('vm');

// Setup a minimal DOM-like environment so we can execute the confirmation
// logic without a browser. `dummyForm` captures the submit handler and the
// sandbox provides document APIs.  We'll run two scenarios to cover both
// outcomes of confirm(): first returning false to mimic the user cancelling
// the prompt and then returning true to verify the positive flow.

function runScenario(confirmFn) {
  const form = {
    addEventListener(event, handler) { this.handler = handler; },
    querySelector(selector) { return { value: 'dummy' }; }
  };
  const ctx = {
    document: {
      _form: form,
      getElementById(id) { return id === 'addServiceForm' ? this._form : null; }
    },
    confirm: confirmFn
  };
  vm.createContext(ctx);
  const code = `const addForm = document.getElementById('addServiceForm');\nif (addForm) {\n  addForm.addEventListener('submit', function(e) {\n    const image = this.querySelector('[name="image"]').value;\n    if (!confirm('Install service using image ' + image + '?')) {\n      e.preventDefault();\n    }\n  });\n}`;
  vm.runInContext(code, ctx);
  let prevented = false;
  const event = { preventDefault() { prevented = true; } };
  if (typeof form.handler === 'function') {
    form.handler.call(form, event);
  }
  return prevented;
}

const cancelled = runScenario(() => false);
const proceeded = runScenario(() => true);
console.log(cancelled && !proceeded ? 'PASS' : 'FAIL');
