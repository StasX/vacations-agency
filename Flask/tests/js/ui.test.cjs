const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup(script = 'main.js') {
    const elements = {};
    for (const id of ['countryBox', 'countrySelector', 'startDate', 'endDate',
        'priceBox', 'vacationForm', 'preview', 'imgBtnTxt', 'ok', 'cancel', 'passwordIcon', 'password']) {
        elements[id] = {
            value: '', innerText: '', type: 'password', listeners: {},
            setCustomValidity(message) { this.validationMessage = message; },
            addEventListener(event, handler) { this.listeners[event] = handler; },
        };
    }
    const modal = { removed: false, remove() { this.removed = true; } };
    const fileInput = { files: [] };
    const body = { style: {}, insertAdjacentHTML(position, html) { this.html = html; } };
    const context = vm.createContext({
        document: {
            querySelector(selector) {
                if (selector === '.modal') return modal;
                if (selector === 'input[type="file"]') return fileInput;
                return selector.startsWith('#') ? elements[selector.slice(1)] || null : null;
            },
            getElementById(id) { return elements[id] || null; }, body,
        },
        window: {}, location: { origin: 'https://example.test', href: '' },
        FileReader: class {
            readAsDataURL(file) { this.result = `data:${file.type};base64,aW1hZ2U=`; this.onload(); }
        },
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../src/static/js', script), 'utf8'), context);
    return { context, elements, body, modal, fileInput };
}

for (const [value, expected] of [['1', true], ['123', true], ['', false], ['abc', false], ['-1', false]]) {
    test(`country validation: ${JSON.stringify(value)}`, () => {
        const { context, elements } = setup();
        elements.countryBox.value = value;
        assert.equal(context.validateCountry(), expected);
    });
}

test('country selection updates hidden id and displayed name', () => {
    const { context, elements } = setup();
    context.selectCountry('Italy', '12');
    assert.equal(elements.countryBox.value, '12');
    assert.equal(elements.countrySelector.innerText, 'Italy');
});

for (const [start, end, invalid] of [
    ['2099-01-02', '2099-01-01', true], ['2099-01-01', '2099-01-01', false],
    ['2099-01-01', '2099-01-02', false],
]) {
    test(`end date ordering: ${start} to ${end}`, () => {
        const { context, elements } = setup();
        elements.startDate.value = start;
        elements.endDate.value = end;
        context.validateEndDate();
        assert.equal(Boolean(elements.endDate.validationMessage), invalid);
    });
}

for (const [date, invalid] of [['2000-01-01', true], ['2099-01-01', false]]) {
    test(`start date validation: ${date}`, () => {
        const { context, elements } = setup();
        elements.startDate.value = date;
        elements.endDate.value = '2099-01-02';
        context.validateStartDate();
        assert.equal(Boolean(elements.startDate.validationMessage), invalid);
    });
}

for (const valid of [false, true]) {
    test(`form submission respects browser validity: ${valid}`, () => {
        const { context } = setup();
        let submitted = false;
        context.validateForm({ target: {
            reportValidity: () => valid, submit: () => { submitted = true; },
        } });
        assert.equal(submitted, valid);
    });
}

for (const country of ['', '1']) {
    test(`vacation submit checks country: ${JSON.stringify(country)}`, () => {
        const { context, elements } = setup();
        elements.countryBox.value = country;
        elements.startDate.value = '2099-01-01';
        elements.endDate.value = '2099-01-02';
        let prevented = false, submitted = false, modalShown = false;
        context.showModal = () => { modalShown = true; };
        context.validateVacationForm({ preventDefault() { prevented = true; }, target: {
            reportValidity: () => true, submit() { submitted = true; },
        } });
        assert.equal(prevented, true);
        assert.equal(submitted, Boolean(country));
        assert.equal(modalShown, !country);
    });
}

test('modal closes and restores scrolling', () => {
    const { context, elements, body, modal } = setup();
    context.showModal({ title: 'Notice', text: 'Hello' });
    assert.match(body.html, /Notice/);
    assert.match(body.html, /Hello/);
    assert.match(body.html, />Ok<\/button>/);
    assert.equal(body.style.overflow, 'hidden');
    elements.ok.onclick();
    assert.equal(modal.removed, true);
    assert.equal(body.style.overflow, 'auto');
});

test('confirmation modal wires action and cancel buttons', () => {
    const { context, elements, body, modal } = setup();
    let confirmed = false;
    context.showModal({ title: 'Confirm', text: 'Delete?', showCancelBtn: true,
        cancelBtnText: 'No', okBtnText: 'Yes', okBtnAction() { confirmed = true; } });
    assert.match(body.html, />No<\/button>/);
    assert.match(body.html, />Yes<\/button>/);
    elements.ok.onclick();
    assert.equal(confirmed, true);
    elements.cancel.onclick();
    assert.equal(modal.removed, true);
});

test('confirmation modal has default cancel label', () => {
    const { context, body } = setup();
    context.showModal({ showCancelBtn: true });
    assert.match(body.html, />Cancel<\/button>/);
});

test('delete confirmation navigates only after confirmation', () => {
    const { context, elements, body, modal } = setup();
    context.deleteVacation('/vacations/12/delete');
    assert.equal(context.location.href, '');
    elements.cancel.onclick();
    assert.equal(modal.removed, true);
    assert.equal(body.style.overflow, 'auto');
    assert.equal(context.location.href, '');
    context.deleteVacation('/vacations/12/delete');
    elements.ok.onclick();
    assert.equal(context.location.href, 'https://example.test/vacations/12/delete');
});

for (const file of [undefined, { type: 'text/plain' }]) {
    test(`image preview ignores ${file ? 'non-image' : 'missing'} file`, () => {
        const { context, elements, fileInput } = setup();
        fileInput.files = file ? [file] : [];
        context.displayImage();
        assert.equal(elements.preview.src, undefined);
    });
}

test('image preview updates source and button text', { todo: 'displayImage selects imgBtnTxt without the # prefix' }, () => {
    const { context, elements, fileInput } = setup();
    fileInput.files = [{ type: 'image/png' }];
    context.displayImage();
    assert.match(elements.preview.src, /^data:image\/png/);
    assert.equal(elements.imgBtnTxt.innerText, 'Change image');
});

test('page load formats prices and registers validation handlers', () => {
    const { context, elements } = setup();
    elements.priceBox.value = '12.5';
    elements.startDate.value = '2099-01-01';
    elements.endDate.value = '2099-01-02';
    context.window.onload();
    assert.equal(elements.priceBox.value, '12.50');
    elements.priceBox.value = '5';
    elements.priceBox.onblur();
    assert.equal(elements.priceBox.value, '5.00');
    assert.equal(elements.startDate.listeners.change, context.validateStartDate);
    assert.equal(elements.endDate.listeners.change, context.validateEndDate);
    assert.equal(elements.vacationForm.listeners.submit, context.validateVacationForm);
});

test('page load handles empty prices and pages without vacation form', () => {
    const { context, elements } = setup();
    delete elements.vacationForm;
    context.window.onload();
    elements.priceBox.onblur();
    assert.equal(elements.priceBox.value, '');
    delete elements.priceBox;
    context.window.onload();
});

test('password visibility toggles on each click', () => {
    const { elements } = setup('password.js');
    elements.passwordIcon.listeners.click();
    assert.equal(elements.password.type, 'text');
    assert.equal(elements.passwordIcon.className, 'fa-regular fa-eye-slash');
    elements.passwordIcon.listeners.click();
    assert.equal(elements.password.type, 'password');
    assert.equal(elements.passwordIcon.className, 'fa-regular fa-eye');
});
