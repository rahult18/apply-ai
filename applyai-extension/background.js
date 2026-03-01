import { API_BASE_URL } from './shared/config.js';

function storageGet(keys) {
    return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function storageSet(obj) {
    return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
}

async function ensureInstallId() {
    const { installId } = await storageGet(["installId"]);
    if (installId) return installId;

    const newId = crypto.randomUUID();
    await storageSet({ installId: newId });
    return newId;
}

chrome.runtime.onInstalled.addListener(() => {
    ensureInstallId().catch(() => { });
});

/**
 * Helper: get active tab (current window)
 */
async function getActiveTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs?.[0] || null;
}

/**
 * Helper: extract DOM HTML via on-demand injection (Option B)
 */
async function extractDomHtmlFromTab(tabId) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            try {
                console.log("ApplyAI: extracting DOM HTML from page");
                return {
                    url: location.href,
                    dom_html: document.documentElement?.outerHTML || ""
                };
            } catch (e) {
                console.log("ApplyAI: DOM extraction error", e);
                return { url: location.href, dom_html: "" };
            }
        }
    });

    return result || { url: "", dom_html: "" };
}

/**
 * Helper: Log autofill event to backend (fire and forget)
 */
async function logAutofillEvent(runId, eventType, payload = {}) {
    try {
        const { extensionToken } = await storageGet(["extensionToken"]);
        if (!extensionToken || !runId) return;

        await fetch(`${API_BASE_URL}/extension/autofill/event`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${extensionToken}`
            },
            body: JSON.stringify({
                run_id: runId,
                event_type: eventType,
                payload
            })
        });
        console.log(`ApplyAI: logged event '${eventType}' for run ${runId}`);
    } catch (e) {
        // Fire and forget - don't block on logging errors
        console.warn("ApplyAI: failed to log event", e);
    }
}

async function extractFormFieldsFromTab(tabId) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            console.log("ApplyAI: extracting form fields from page");

            // Helper: Sleep utility
            const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

            // Helper: Find label for an input
            function findLabelForInput(element) {
                if (element.id) {
                    const label = document.querySelector(`label[for="${element.id}"]`);
                    if (label) return label.textContent.trim();
                }

                let parent = element.parentElement;
                while (parent && parent.tagName !== 'BODY') {
                    if (parent.tagName === 'LABEL') {
                        return parent.textContent.trim();
                    }
                    parent = parent.parentElement;
                }

                const prevSibling = element.previousElementSibling;
                if (prevSibling && prevSibling.tagName === 'LABEL') {
                    return prevSibling.textContent.trim();
                }

                if (element.getAttribute('aria-label')) {
                    return element.getAttribute('aria-label');
                }

                if (element.placeholder) {
                    return element.placeholder;
                }

                return null;
            }

            // Helper: Generate CSS selector
            function generateSelector(element) {
                if (element.id) {
                    // Use attribute selector if ID starts with digit (CSS can't parse #4012870007)
                    if (/^\d/.test(element.id)) {
                        return `[id="${element.id}"]`;
                    }
                    return `#${element.id}`;
                }

                if (element.name) {
                    return `[name="${element.name}"]`;
                }

                const path = [];
                let current = element;
                while (current && current.tagName !== 'BODY') {
                    let selector = current.tagName.toLowerCase();
                    if (current.className) {
                        const classes = current.className.split(' ').filter(c => c && !c.startsWith('css-'));
                        if (classes.length > 0) {
                            selector += `.${classes[0]}`;
                        }
                    }
                    path.unshift(selector);
                    current = current.parentElement;
                }

                return path.slice(-3).join(' > ');
            }

            // Helper: Check if field is required
            function isRequired(element) {
                if (element.required) return true;
                if (element.getAttribute('aria-required') === 'true') return true;

                const label = findLabelForInput(element);
                if (label && label.includes('*')) return true;

                return false;
            }

            // Helper: Try to open a React Select dropdown
            async function tryOpenReactSelect(combobox) {
                try {
                    combobox.focus();
                    await sleep(100);

                    // Dispatch proper mouse events
                    combobox.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                    await sleep(50);
                    combobox.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                    await sleep(50);
                    combobox.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                    await sleep(100);

                    // Try arrow down key
                    combobox.dispatchEvent(new KeyboardEvent('keydown', {
                        key: 'ArrowDown',
                        code: 'ArrowDown',
                        keyCode: 40,
                        bubbles: true,
                        cancelable: true
                    }));
                    await sleep(100);

                    // Try to find and click the dropdown indicator
                    const container = combobox.closest('[class*="select"]');
                    if (container) {
                        const indicator = container.querySelector('[class*="indicator"], [class*="arrow"], [class*="dropdown"]');
                        if (indicator) {
                            indicator.click();
                            await sleep(100);
                        }
                    }

                    await sleep(300); // Wait for options to render
                    return true;
                } catch (error) {
                    return false;
                }
            }

            // Helper: Extract options from select/combobox
            function extractOptions(element) {
                const options = [];

                if (element.tagName === 'SELECT') {
                    const optionElements = element.querySelectorAll('option');
                    optionElements.forEach(opt => {
                        if (opt.value) {
                            options.push({
                                value: opt.value,
                                label: opt.textContent.trim()
                            });
                        }
                    });
                }

                // For combobox, check multiple possible locations for options
                if (element.getAttribute('role') === 'combobox') {
                    // Method 1: Check aria-controls
                    const listboxId = element.getAttribute('aria-controls');
                    if (listboxId) {
                        const listbox = document.getElementById(listboxId);
                        if (listbox) {
                            const optionElements = listbox.querySelectorAll('[role="option"]');
                            optionElements.forEach(opt => {
                                options.push({
                                    value: opt.getAttribute('data-value') || opt.textContent.trim(),
                                    label: opt.textContent.trim()
                                });
                            });
                        }
                    }

                    // Method 2: Look for menu container (React Select pattern)
                    if (options.length === 0) {
                        const menuContainers = document.querySelectorAll('[class*="menu"], [class*="Menu"]');
                        menuContainers.forEach(menu => {
                            const menuOptions = menu.querySelectorAll('[role="option"]');
                            if (menuOptions.length > 0) {
                                menuOptions.forEach(opt => {
                                    options.push({
                                        value: opt.getAttribute('data-value') || opt.textContent.trim(),
                                        label: opt.textContent.trim()
                                    });
                                });
                            }
                        });
                    }
                }

                return options;
            }

            // Helper: Check if input should be skipped
            function shouldSkipInput(input) {
                if (input.className && input.className.includes('requiredInput')) {
                    return true;
                }

                const selectContainer = input.closest('.select__container, .select-shell');
                if (selectContainer && input.getAttribute('role') !== 'combobox') {
                    return true;
                }

                if (!input.id && !input.name && !input.placeholder && input.getAttribute('role') !== 'combobox') {
                    return true;
                }

                return false;
            }

            // Main extraction function (async to support dropdown interaction)
            async function extractFormFields() {
                const fields = [];

                // Step 1: Try to open all combobox/React Select dropdowns first
                const comboboxes = document.querySelectorAll('[role="combobox"]');
                for (const combobox of comboboxes) {
                    await tryOpenReactSelect(combobox);
                }

                // Extract standard input fields
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"])');
                inputs.forEach(input => {
                    if (shouldSkipInput(input)) {
                        return;
                    }

                    fields.push({
                        type: 'input',
                        inputType: input.type || 'text',
                        name: input.name || null,
                        id: input.id || null,
                        label: findLabelForInput(input),
                        placeholder: input.placeholder || null,
                        required: isRequired(input),
                        value: input.value || null,
                        selector: generateSelector(input),
                        autocomplete: input.getAttribute('autocomplete') || null
                    });
                });

                // Extract textarea fields
                const textareas = document.querySelectorAll('textarea');
                textareas.forEach(textarea => {
                    fields.push({
                        type: 'textarea',
                        inputType: 'textarea',
                        name: textarea.name || null,
                        id: textarea.id || null,
                        label: findLabelForInput(textarea),
                        placeholder: textarea.placeholder || null,
                        required: isRequired(textarea),
                        value: textarea.value || null,
                        selector: generateSelector(textarea),
                        maxLength: textarea.maxLength > 0 ? textarea.maxLength : null
                    });
                });

                // Extract select fields
                const selects = document.querySelectorAll('select');
                selects.forEach(select => {
                    fields.push({
                        type: 'select',
                        inputType: 'select',
                        name: select.name || null,
                        id: select.id || null,
                        label: findLabelForInput(select),
                        required: isRequired(select),
                        value: select.value || null,
                        selector: generateSelector(select),
                        options: extractOptions(select)
                    });
                });

                // Extract React Select / Combobox fields (after trying to open them)
                comboboxes.forEach(combobox => {
                    if (combobox.tagName === 'INPUT') {
                        const existingIndex = fields.findIndex(f => f.id === combobox.id);
                        if (existingIndex >= 0) {
                            fields[existingIndex].isCombobox = true;
                            fields[existingIndex].options = extractOptions(combobox);
                            return;
                        }
                    }

                    fields.push({
                        type: 'combobox',
                        inputType: 'select',
                        name: combobox.getAttribute('name') || null,
                        id: combobox.id || null,
                        label: findLabelForInput(combobox),
                        placeholder: combobox.getAttribute('placeholder') || null,
                        required: isRequired(combobox),
                        selector: generateSelector(combobox),
                        options: extractOptions(combobox),
                        ariaLabel: combobox.getAttribute('aria-label') || null
                    });
                });

                // Extract radio button groups
                const radioInputs = document.querySelectorAll('input[type="radio"]');
                const radioGroups = {};

                radioInputs.forEach(radio => {
                    const name = radio.name;
                    if (!name) return;

                    if (!radioGroups[name]) {
                        radioGroups[name] = {
                            type: 'radio',
                            inputType: 'radio',
                            name: name,
                            label: findLabelForInput(radio) || name,
                            required: isRequired(radio),
                            options: [],
                            selector: `input[name="${name}"]`
                        };
                    }

                    radioGroups[name].options.push({
                        value: radio.value,
                        label: findLabelForInput(radio) || radio.value,
                        id: radio.id,
                        checked: radio.checked
                    });
                });

                fields.push(...Object.values(radioGroups));

                // Extract checkbox groups
                const checkboxInputs = document.querySelectorAll('input[type="checkbox"]');
                const checkboxGroups = {};

                checkboxInputs.forEach(checkbox => {
                    const name = checkbox.name;
                    if (!name) {
                        fields.push({
                            type: 'checkbox',
                            inputType: 'checkbox',
                            name: name,
                            id: checkbox.id || null,
                            label: findLabelForInput(checkbox),
                            required: isRequired(checkbox),
                            value: checkbox.value,
                            checked: checkbox.checked,
                            selector: generateSelector(checkbox)
                        });
                        return;
                    }

                    if (!checkboxGroups[name]) {
                        checkboxGroups[name] = {
                            type: 'checkbox-group',
                            inputType: 'checkbox',
                            name: name,
                            label: name,
                            required: isRequired(checkbox),
                            options: [],
                            selector: `input[name="${name}"]`
                        };
                    }

                    checkboxGroups[name].options.push({
                        value: checkbox.value,
                        label: findLabelForInput(checkbox) || checkbox.value,
                        id: checkbox.id,
                        checked: checkbox.checked
                    });
                });

                fields.push(...Object.values(checkboxGroups));

                return fields;
            }

            // Execute the extraction
            return extractFormFields().then(fields => {
                console.log("ApplyAI: extracted form fields", fields.length);
                return fields;
            }).catch(error => {
                console.error("ApplyAI: form field extraction error", error);
                return [];
            });
        }
    });

    return result || [];
}

/**
 * Enhanced form field extraction with dropdown interaction
 * This function tries to open React Select and native dropdowns to extract their options
 */
async function extractFormFieldsWithDropdownInteraction(tabId) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            console.log("🐛 ApplyAI DEBUG: Starting enhanced form field extraction with dropdown interaction");

            // Helper: Sleep utility
            const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

            // Helper: Find label for an input
            function findLabelForInput(element) {
                if (element.id) {
                    const label = document.querySelector(`label[for="${element.id}"]`);
                    if (label) return label.textContent.trim();
                }

                let parent = element.parentElement;
                while (parent && parent.tagName !== 'BODY') {
                    if (parent.tagName === 'LABEL') {
                        return parent.textContent.trim();
                    }
                    parent = parent.parentElement;
                }

                const prevSibling = element.previousElementSibling;
                if (prevSibling && prevSibling.tagName === 'LABEL') {
                    return prevSibling.textContent.trim();
                }

                if (element.getAttribute('aria-label')) {
                    return element.getAttribute('aria-label');
                }

                if (element.placeholder) {
                    return element.placeholder;
                }

                return null;
            }

            // Helper: Generate CSS selector
            function generateSelector(element) {
                if (element.id) {
                    if (/^\d/.test(element.id)) {
                        return `[id="${element.id}"]`;
                    }
                    return `#${element.id}`;
                }

                if (element.name) {
                    return `[name="${element.name}"]`;
                }

                const path = [];
                let current = element;
                while (current && current.tagName !== 'BODY') {
                    let selector = current.tagName.toLowerCase();
                    if (current.className) {
                        const classes = current.className.split(' ').filter(c => c && !c.startsWith('css-'));
                        if (classes.length > 0) {
                            selector += `.${classes[0]}`;
                        }
                    }
                    path.unshift(selector);
                    current = current.parentElement;
                }

                return path.slice(-3).join(' > ');
            }

            // Helper: Check if field is required
            function isRequired(element) {
                if (element.required) return true;
                if (element.getAttribute('aria-required') === 'true') return true;

                const label = findLabelForInput(element);
                if (label && label.includes('*')) return true;

                return false;
            }

            // Helper: Try to open a React Select dropdown
            async function tryOpenReactSelect(combobox) {
                try {
                    combobox.focus();
                    await sleep(100);

                    // Dispatch proper mouse events
                    combobox.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                    await sleep(50);
                    combobox.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                    await sleep(50);
                    combobox.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                    await sleep(100);

                    // Try arrow down key
                    combobox.dispatchEvent(new KeyboardEvent('keydown', {
                        key: 'ArrowDown',
                        code: 'ArrowDown',
                        keyCode: 40,
                        bubbles: true,
                        cancelable: true
                    }));
                    await sleep(100);

                    // Try to find and click the dropdown indicator
                    const container = combobox.closest('[class*="select"]');
                    if (container) {
                        const indicator = container.querySelector('[class*="indicator"], [class*="arrow"], [class*="dropdown"]');
                        if (indicator) {
                            indicator.click();
                            await sleep(100);
                        }
                    }

                    await sleep(300); // Wait for options to render
                    return true;
                } catch (error) {
                    return false;
                }
            }

            // Helper: Extract options from select/combobox (enhanced)
            function extractOptions(element) {
                const options = [];

                if (element.tagName === 'SELECT') {
                    const optionElements = element.querySelectorAll('option');
                    optionElements.forEach(opt => {
                        if (opt.value) {
                            options.push({
                                value: opt.value,
                                label: opt.textContent.trim()
                            });
                        }
                    });
                }

                // For combobox, check multiple possible locations for options
                if (element.getAttribute('role') === 'combobox') {
                    // Method 1: Check aria-controls
                    const listboxId = element.getAttribute('aria-controls');
                    if (listboxId) {
                        const listbox = document.getElementById(listboxId);
                        if (listbox) {
                            const optionElements = listbox.querySelectorAll('[role="option"]');
                            optionElements.forEach(opt => {
                                options.push({
                                    value: opt.getAttribute('data-value') || opt.textContent.trim(),
                                    label: opt.textContent.trim()
                                });
                            });
                        }
                    }

                    // Method 2: Look for menu container (React Select pattern)
                    if (options.length === 0) {
                        const menuContainers = document.querySelectorAll('[class*="menu"], [class*="Menu"]');
                        menuContainers.forEach(menu => {
                            const menuOptions = menu.querySelectorAll('[role="option"]');
                            if (menuOptions.length > 0) {
                                menuOptions.forEach(opt => {
                                    options.push({
                                        value: opt.getAttribute('data-value') || opt.textContent.trim(),
                                        label: opt.textContent.trim()
                                    });
                                });
                            }
                        });
                    }
                }

                return options;
            }

            // Helper: Check if input should be skipped
            function shouldSkipInput(input) {
                if (input.className && input.className.includes('requiredInput')) {
                    return true;
                }

                const selectContainer = input.closest('.select__container, .select-shell');
                if (selectContainer && input.getAttribute('role') !== 'combobox') {
                    return true;
                }

                if (!input.id && !input.name && !input.placeholder && input.getAttribute('role') !== 'combobox') {
                    return true;
                }

                return false;
            }

            // Main extraction function (async version with dropdown interaction)
            async function extractFormFieldsWithInteraction() {
                const fields = [];

                // Step 1: Try to open all combobox/React Select dropdowns
                const comboboxes = document.querySelectorAll('[role="combobox"]');
                for (const combobox of comboboxes) {
                    await tryOpenReactSelect(combobox);
                }

                // Extract standard input fields
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"])');

                inputs.forEach(input => {
                    if (shouldSkipInput(input)) {
                        return;
                    }

                    fields.push({
                        type: 'input',
                        inputType: input.type || 'text',
                        name: input.name || null,
                        id: input.id || null,
                        label: findLabelForInput(input),
                        placeholder: input.placeholder || null,
                        required: isRequired(input),
                        value: input.value || null,
                        selector: generateSelector(input),
                        autocomplete: input.getAttribute('autocomplete') || null
                    });
                });

                // Extract textarea fields
                const textareas = document.querySelectorAll('textarea');

                textareas.forEach(textarea => {
                    fields.push({
                        type: 'textarea',
                        inputType: 'textarea',
                        name: textarea.name || null,
                        id: textarea.id || null,
                        label: findLabelForInput(textarea),
                        placeholder: textarea.placeholder || null,
                        required: isRequired(textarea),
                        value: textarea.value || null,
                        selector: generateSelector(textarea),
                        maxLength: textarea.maxLength > 0 ? textarea.maxLength : null
                    });
                });

                // Extract select fields
                const selects = document.querySelectorAll('select');

                selects.forEach(select => {
                    const options = extractOptions(select);
                    fields.push({
                        type: 'select',
                        inputType: 'select',
                        name: select.name || null,
                        id: select.id || null,
                        label: findLabelForInput(select),
                        required: isRequired(select),
                        value: select.value || null,
                        selector: generateSelector(select),
                        options: options
                    });
                });

                // Extract React Select / Combobox fields (after trying to open them)
                comboboxes.forEach(combobox => {
                    if (combobox.tagName === 'INPUT') {
                        const existingIndex = fields.findIndex(f => f.id === combobox.id);
                        if (existingIndex >= 0) {
                            const options = extractOptions(combobox);
                            fields[existingIndex].isCombobox = true;
                            fields[existingIndex].options = options;
                            return;
                        }
                    }

                    const options = extractOptions(combobox);

                    fields.push({
                        type: 'combobox',
                        inputType: 'select',
                        name: combobox.getAttribute('name') || null,
                        id: combobox.id || null,
                        label: findLabelForInput(combobox),
                        placeholder: combobox.getAttribute('placeholder') || null,
                        required: isRequired(combobox),
                        selector: generateSelector(combobox),
                        options: options,
                        ariaLabel: combobox.getAttribute('aria-label') || null
                    });
                });

                // Extract radio button groups
                const radioInputs = document.querySelectorAll('input[type="radio"]');
                const radioGroups = {};

                radioInputs.forEach(radio => {
                    const name = radio.name;
                    if (!name) return;

                    if (!radioGroups[name]) {
                        radioGroups[name] = {
                            type: 'radio',
                            inputType: 'radio',
                            name: name,
                            label: findLabelForInput(radio) || name,
                            required: isRequired(radio),
                            options: [],
                            selector: `input[name="${name}"]`
                        };
                    }

                    radioGroups[name].options.push({
                        value: radio.value,
                        label: findLabelForInput(radio) || radio.value,
                        id: radio.id,
                        checked: radio.checked
                    });
                });

                fields.push(...Object.values(radioGroups));

                // Extract checkbox groups
                const checkboxInputs = document.querySelectorAll('input[type="checkbox"]');
                const checkboxGroups = {};

                checkboxInputs.forEach(checkbox => {
                    const name = checkbox.name;
                    if (!name) {
                        fields.push({
                            type: 'checkbox',
                            inputType: 'checkbox',
                            name: name,
                            id: checkbox.id || null,
                            label: findLabelForInput(checkbox),
                            required: isRequired(checkbox),
                            value: checkbox.value,
                            checked: checkbox.checked,
                            selector: generateSelector(checkbox)
                        });
                        return;
                    }

                    if (!checkboxGroups[name]) {
                        checkboxGroups[name] = {
                            type: 'checkbox-group',
                            inputType: 'checkbox',
                            name: name,
                            label: name,
                            required: isRequired(checkbox),
                            options: [],
                            selector: `input[name="${name}"]`
                        };
                    }

                    checkboxGroups[name].options.push({
                        value: checkbox.value,
                        label: findLabelForInput(checkbox) || checkbox.value,
                        id: checkbox.id,
                        checked: checkbox.checked
                    });
                });

                fields.push(...Object.values(checkboxGroups));

                return fields;
            }

            // Execute the extraction
            return extractFormFieldsWithInteraction().then(fields => {
                const fieldsWithOptions = fields.filter(f => f.options && f.options.length > 0);
                const fieldsWithoutOptions = fields.filter(f =>
                    (f.type === 'select' || f.type === 'combobox') &&
                    (!f.options || f.options.length === 0)
                );

                console.log("🐛 ========================================");
                console.log("🐛 EXTRACTION COMPLETE");
                console.log(`🐛 Total fields: ${fields.length}`);
                console.log(`🐛 Fields with options: ${fieldsWithOptions.length}`);

                if (fieldsWithoutOptions.length > 0) {
                    console.warn(`🐛 WARNING: ${fieldsWithoutOptions.length} dropdowns with no options`);
                    fieldsWithoutOptions.forEach(field => {
                        console.warn(`  - ${field.label || field.id || field.name}`);
                    });
                }

                console.log("🐛 Full data available in console");
                console.log("🐛 ========================================");
                console.table(fields.map(f => ({
                    type: f.type,
                    label: f.label || '(no label)',
                    options: f.options ? f.options.length : 'N/A'
                })));
                console.log(fields);

                return fields;
            }).catch(error => {
                console.error("🐛 ERROR during extraction:", error);
                return [];
            });
        }
    });

    return result || [];
}

async function applyAutofillPlanToTab(tabId, planJson, resumeUrl) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: async (plan, resumeFileUrl) => {
            console.log("ApplyAI: applying autofill plan in page context", {
                totalFields: Array.isArray(plan?.fields) ? plan.fields.length : 0
            });
            const cssEscape = (value) => {
                if (window.CSS && typeof window.CSS.escape === "function") {
                    return window.CSS.escape(value);
                }
                return String(value).replace(/"/g, '\\"');
            };

            const toBoolean = (value) => {
                if (typeof value === "boolean") return value;
                if (typeof value === "number") return value !== 0;
                if (typeof value === "string") {
                    const normalized = value.trim().toLowerCase();
                    if (["true", "yes", "y", "1"].includes(normalized)) return true;
                    if (["false", "no", "n", "0"].includes(normalized)) return false;
                }
                return Boolean(value);
            };

            const dispatchEvents = (el) => {
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
            };

            const normalizeText = (text) => {
                return String(text ?? "")
                    .toLowerCase()
                    .trim()
                    .replace(/\s+/g, " ")
                    .replace(/[^a-z0-9 ]+/g, "");
            };

            const selectOption = (el, value) => {
                const targetRaw = value == null ? "" : String(value);
                const targetNorm = normalizeText(targetRaw);
                const synonymMap = {
                    us: "united states",
                    usa: "united states",
                    "united states of america": "united states"
                };
                const altTarget = synonymMap[targetNorm] || targetNorm;
                const targets = Array.from(new Set([targetNorm, altTarget].filter(Boolean)));

                const tag = (el.tagName || "").toLowerCase();
                const role = (el.getAttribute("role") || "").toLowerCase();
                const ariaAutocomplete = el.getAttribute("aria-autocomplete");

                // Detect React select (input with role=combobox or aria-autocomplete)
                const isReactSelect = tag === "input" && (role === "combobox" || ariaAutocomplete === "list");

                if (isReactSelect) {
                    console.log("ApplyAI: detected React select", {
                        targetRaw,
                        targets,
                        role,
                        ariaAutocomplete
                    });

                    try {
                        // Focus the input
                        el.focus();

                        // Set value using native setter to trigger React
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype,
                            "value"
                        ).set;
                        nativeInputValueSetter.call(el, targetRaw);

                        // Trigger React events
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                        el.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));

                        // Wait a bit for dropdown to render
                        setTimeout(() => {
                            // Try to find and click the matching option from the dropdown
                            const listboxId = el.getAttribute("aria-controls") || el.getAttribute("aria-owns");
                            let listbox = null;

                            if (listboxId) {
                                listbox = document.getElementById(listboxId);
                            }

                            // Fallback: look for common react-select patterns
                            if (!listbox) {
                                const elId = el.getAttribute("id");
                                if (elId) {
                                    // react-select pattern: react-select-{id}-listbox
                                    listbox = document.getElementById(`react-select-${elId}-listbox`);
                                }
                            }

                            // Fallback: find any visible listbox near this element
                            if (!listbox) {
                                const nearbyListbox = document.querySelector('[role="listbox"]:not([aria-hidden="true"])');
                                if (nearbyListbox) {
                                    listbox = nearbyListbox;
                                }
                            }

                            if (listbox) {
                                const optionElements = Array.from(listbox.querySelectorAll('[role="option"]'));
                                console.log("ApplyAI: React select found options", {
                                    targetRaw,
                                    optionCount: optionElements.length
                                });

                                // Try exact match first
                                const exactMatch = optionElements.find((opt) => {
                                    const optText = normalizeText(opt.textContent || "");
                                    return targets.some((t) => t === optText);
                                });

                                if (exactMatch) {
                                    console.log("ApplyAI: React select exact match, clicking", {
                                        targetRaw,
                                        match: exactMatch.textContent
                                    });
                                    exactMatch.click();
                                    return;
                                }

                                // Try contains match
                                let best = null;
                                let bestLen = 0;
                                for (const opt of optionElements) {
                                    const optText = normalizeText(opt.textContent || "");
                                    for (const t of targets) {
                                        if (!t) continue;
                                        if (optText.includes(t) || t.includes(optText)) {
                                            if (optText.length > bestLen) {
                                                best = opt;
                                                bestLen = optText.length;
                                            }
                                        }
                                    }
                                }

                                if (best) {
                                    console.log("ApplyAI: React select contains match, clicking", {
                                        targetRaw,
                                        match: best.textContent
                                    });
                                    best.click();
                                }
                            } else {
                                console.log("ApplyAI: React select listbox not found, value typed");
                            }
                        }, 300);

                        return { applied: true, matchMethod: "react_select_typed" };
                    } catch (err) {
                        console.error("ApplyAI: React select error", err);
                        return { applied: false, matchMethod: "react_select_error" };
                    }
                }

                // Native select handling
                const options = Array.from(el.options || []);
                console.log("ApplyAI: native select options", {
                    targetRaw,
                    targets,
                    optionCount: options.length
                });
                const exactMatch = options.find((opt) => {
                    const optValue = normalizeText(opt.value);
                    const optText = normalizeText(opt.textContent || "");
                    return targets.some((t) => t === optValue || t === optText);
                });
                if (exactMatch) {
                    console.log("ApplyAI: native select exact match", {
                        targetRaw,
                        match: exactMatch.value
                    });
                    el.value = exactMatch.value;
                    dispatchEvents(el);
                    return { applied: true, matchMethod: "exact" };
                }

                let best = null;
                let bestLen = 0;
                for (const opt of options) {
                    const optValue = normalizeText(opt.value);
                    const optText = normalizeText(opt.textContent || "");
                    for (const t of targets) {
                        if (!t) continue;
                        const valueMatch = optValue && (optValue.includes(t) || t.includes(optValue));
                        const textMatch = optText && (optText.includes(t) || t.includes(optText));
                        if (valueMatch || textMatch) {
                            const candLen = Math.max(optValue.length, optText.length);
                            if (candLen > bestLen) {
                                best = opt;
                                bestLen = candLen;
                            }
                        }
                    }
                }

                if (best) {
                    console.log("ApplyAI: native select contains match", {
                        targetRaw,
                        match: best.value
                    });
                    el.value = best.value;
                    dispatchEvents(el);
                    return { applied: true, matchMethod: "contains" };
                }

                console.log("ApplyAI: select no match", { targetRaw });
                return { applied: false, matchMethod: "no_match" };
            };

            const fillFileInput = async (el, fileUrl) => {
                if (!fileUrl) return false;
                try {
                    const resp = await fetch(fileUrl);
                    if (!resp.ok) return false;
                    const blob = await resp.blob();
                    const fileName = fileUrl.split("/").pop().split("?")[0] || "resume.pdf";
                    const file = new File([blob], fileName, { type: blob.type || "application/pdf" });
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    el.files = dt.files;
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    console.log("ApplyAI: fillFileInput success", { fileName, size: blob.size });
                    return true;
                } catch (err) {
                    console.error("ApplyAI: fillFileInput error", err);
                    return false;
                }
            };

            const fillTextInput = (el, value) => {
                if (value == null) return false;
                const tag = (el.tagName || "").toLowerCase();
                if (tag === "input" && (el.getAttribute("type") || "").toLowerCase() === "file") {
                    return false;
                }
                console.log("ApplyAI: fillTextInput", {
                    id: el.getAttribute("id"),
                    name: el.getAttribute("name"),
                    value
                });
                el.value = typeof value === "string" ? value : JSON.stringify(value);
                dispatchEvents(el);
                return true;
            };

            const fillRadioGroup = (nodes, value) => {
                if (value == null) return false;
                const target = String(value).trim().toLowerCase();
                let matched = false;
                for (const node of nodes) {
                    const nodeValue = (node.value || "").trim().toLowerCase();
                    if (nodeValue && nodeValue === target) {
                        console.log("ApplyAI: fillRadioGroup match", {
                            target,
                            nodeValue
                        });
                        node.checked = true;
                        dispatchEvents(node);
                        matched = true;
                        break;
                    }
                }
                return matched;
            };

            const fillCheckboxGroup = (nodes, value) => {
                if (!nodes.length) return false;
                if (Array.isArray(value)) {
                    let changed = false;
                    const normalized = value.map((v) => String(v).trim().toLowerCase());
                    for (const node of nodes) {
                        const nodeValue = (node.value || "").trim().toLowerCase();
                        const shouldCheck = normalized.includes(nodeValue);
                        console.log("ApplyAI: fillCheckboxGroup array", {
                            nodeValue,
                            shouldCheck
                        });
                        node.checked = shouldCheck;
                        dispatchEvents(node);
                        changed = changed || shouldCheck;
                    }
                    return changed;
                }
                const shouldCheck = toBoolean(value);
                for (const node of nodes) {
                    console.log("ApplyAI: fillCheckboxGroup boolean", {
                        nodeValue: (node.value || "").trim(),
                        shouldCheck
                    });
                    node.checked = shouldCheck;
                    dispatchEvents(node);
                }
                return shouldCheck;
            };

            let filled = 0;
            let skipped = 0;
            const errors = [];
            const debug = [];

            const fields = Array.isArray(plan?.fields) ? plan.fields : [];
            for (const field of fields) {
                if (field?.action !== "autofill") {
                    debug.push({
                        question_signature: field?.question_signature || null,
                        action: field?.action || null,
                        selector: field?.selector || null,
                        input_type: field?.input_type || null,
                        value: field?.value ?? null,
                        applied: false,
                        reason: "action_not_autofill"
                    });
                    skipped += 1;
                    continue;
                }

                const selector = field?.selector;
                if (!selector) {
                    debug.push({
                        question_signature: field?.question_signature || null,
                        action: field?.action || null,
                        selector: field?.selector || null,
                        input_type: field?.input_type || null,
                        value: field?.value ?? null,
                        applied: false,
                        reason: "missing_selector"
                    });
                    skipped += 1;
                    continue;
                }

                const nameMatch = selector.match(/^\[name="(.+)"\]$/);
                let nodes = [];
                if (nameMatch) {
                    const name = cssEscape(nameMatch[1]);
                    nodes = Array.from(document.querySelectorAll(`[name="${name}"]`));
                } else {
                    const node = document.querySelector(selector);
                    if (node) nodes = [node];
                }

                // Fallback for numeric IDs that slipped through
                if (!nodes.length && selector.startsWith('#')) {
                    const id = selector.substring(1);
                    // Try attribute selector format
                    const fallbackNodes = document.querySelectorAll(`[id="${id}"]`);
                    if (fallbackNodes.length > 0) {
                        nodes = Array.from(fallbackNodes);
                        console.log('ApplyAI: Used attribute selector fallback for numeric ID', id);
                    }
                }

                if (!nodes.length) {
                    console.log("ApplyAI: no nodes for selector", selector);
                    debug.push({
                        question_signature: field?.question_signature || null,
                        action: field?.action || null,
                        selector,
                        input_type: field?.input_type || null,
                        value: field?.value ?? null,
                        applied: false,
                        reason: "no_nodes_found"
                    });
                    skipped += 1;
                    continue;
                }

                try {
                    const inputType = field?.input_type;
                    const value = field?.value;
                    let applied = false;

                    let matchMethod = null;
                    if (inputType === "file") {
                        if (value === "resume" && resumeFileUrl) {
                            applied = await fillFileInput(nodes[0], resumeFileUrl);
                        } else {
                            applied = false;
                        }
                    } else if (inputType === "select") {
                        const result = selectOption(nodes[0], value);
                        applied = result.applied;
                        matchMethod = result.matchMethod;
                        console.log("ApplyAI: select apply result", {
                            selector,
                            applied,
                            matchMethod
                        });
                    } else if (inputType === "radio") {
                        applied = fillRadioGroup(nodes, value);
                    } else if (inputType === "checkbox") {
                        applied = fillCheckboxGroup(nodes, value);
                    } else {
                        applied = fillTextInput(nodes[0], value);
                    }

                    if (applied) {
                        filled += 1;
                    } else {
                        skipped += 1;
                    }
                    debug.push({
                        question_signature: field?.question_signature || null,
                        action: field?.action || null,
                        selector,
                        input_type: inputType || null,
                        value: value ?? null,
                        applied,
                        reason: applied ? null : `apply_failed${matchMethod ? `:${matchMethod}` : ""}`
                    });
                } catch (err) {
                    errors.push(String(err?.message || err));
                    debug.push({
                        question_signature: field?.question_signature || null,
                        action: field?.action || null,
                        selector,
                        input_type: field?.input_type || null,
                        value: field?.value ?? null,
                        applied: false,
                        reason: `error:${String(err?.message || err)}`
                    });
                    skipped += 1;
                }
            }

            return { filled, skipped, errors, debug };
        },
        args: [planJson, resumeUrl]
    });

    return result || { filled: 0, skipped: 0, errors: [], debug: [] };
}

/**
 * Helper: basic URL scheme guard
 */
function isRestrictedUrl(url) {
    if (!url) return true;
    return (
        url.startsWith("chrome://") ||
        url.startsWith("edge://") ||
        url.startsWith("about:") ||
        url.startsWith("file://")
    );
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
        try {
            /**
             * Existing: connect exchange
             */
            if (message?.type === "APPLYAI_EXTENSION_CONNECT" && message?.code) {
                const installId = await ensureInstallId();

                const res = await fetch(`${API_BASE_URL}/extension/connect/exchange`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        one_time_code: message.code,
                        install_id: installId
                    })
                });

                if (!res.ok) {
                    const text = await res.text().catch(() => "");
                    throw new Error(`Exchange failed: ${res.status} ${text}`);
                }

                const data = await res.json();
                const extensionToken = data.token;

                if (!extensionToken) {
                    throw new Error("Exchange succeeded but no token returned.");
                }

                await storageSet({ extensionToken });

                chrome.runtime.sendMessage({ type: "APPLYAI_EXTENSION_CONNECTED" }, () => {
                    void chrome.runtime.lastError;
                });

                sendResponse({ ok: true });
                return;
            }

            /**
             * DEBUG: Extract form fields with dropdown interaction
             */
            if (message?.type === "APPLYAI_DEBUG_EXTRACT_FIELDS") {
                console.log("🐛 DEBUG: Received debug extraction request");

                const tab = await getActiveTab();
                if (!tab?.id) {
                    sendResponse({ ok: false, error: "No active tab found." });
                    return;
                }

                const tabUrl = tab.url || "";
                if (isRestrictedUrl(tabUrl)) {
                    sendResponse({ ok: false, error: "Cannot access this page (restricted URL)." });
                    return;
                }

                console.log("🐛 DEBUG: Extracting form fields from tab:", tab.id, tabUrl);

                try {
                    const fields = await extractFormFieldsWithDropdownInteraction(tab.id);

                    console.log("🐛 DEBUG: Extraction complete in background script");
                    console.log(`🐛 DEBUG: Extracted ${fields.length} fields`);
                    console.log("🐛 DEBUG: Field summary:", fields.map(f => ({
                        type: f.type,
                        label: f.label || '(no label)',
                        optionCount: f.options ? f.options.length : 0
                    })));

                    sendResponse({
                        ok: true,
                        fieldCount: fields.length,
                        fields: fields
                    });
                } catch (error) {
                    console.error("🐛 DEBUG: Extraction error:", error);
                    sendResponse({
                        ok: false,
                        error: error.message || "Unknown error during extraction"
                    });
                }
                return;
            }

            /**
             * New: Extract JD
             */
            if (message?.type === "APPLYAI_EXTRACT_JD") {
                // progress helper
                const progress = (stage) => {
                    chrome.runtime.sendMessage({ type: "APPLYAI_EXTRACT_JD_PROGRESS", stage }, () => {
                        void chrome.runtime.lastError;
                    });
                };

                progress("starting");

                const { extensionToken } = await storageGet(["extensionToken"]);
                if (!extensionToken) {
                    sendResponse({ ok: false, error: "Not connected. Please connect first." });
                    return;
                }

                const tab = await getActiveTab();
                if (!tab?.id) {
                    sendResponse({ ok: false, error: "No active tab found." });
                    return;
                }

                const tabUrl = tab.url || "";
                if (isRestrictedUrl(tabUrl)) {
                    sendResponse({ ok: false, error: "Cannot access this page." });
                    return;
                }

                progress("extracting_dom");

                let { url, dom_html } = await extractDomHtmlFromTab(tab.id);

                // fallback to tab.url if injection didn't return it
                if (!url) url = tabUrl;

                // size guard: if HTML is too large, drop it and let backend fallback to URL fetch
                const MAX_HTML_CHARS = 2_500_000; // ~2.5MB as characters; adjust later
                if (dom_html && dom_html.length > MAX_HTML_CHARS) {
                    dom_html = null;
                }

                progress("sending_to_backend");

                const ingestRes = await fetch(`${API_BASE_URL}/extension/jobs/ingest`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${extensionToken}`
                    },
                    body: JSON.stringify({
                        job_link: url,
                        dom_html: dom_html || null
                    })
                });

                if (ingestRes.status === 401) {
                    // token invalid/expired
                    await storageSet({ extensionToken: null });
                    sendResponse({ ok: false, error: "Session expired. Please connect again." });
                    return;
                }

                if (!ingestRes.ok) {
                    const text = await ingestRes.text().catch(() => "");
                    sendResponse({ ok: false, error: `Ingest failed: ${ingestRes.status} ${text}` });
                    return;
                }

                const ingestData = await ingestRes.json().catch(() => ({}));

                const jobTitle = ingestData?.job_title || null;
                const company = ingestData?.company || null;

                // persist last result (not used by popup now, but kept for debugging)
                await storageSet({
                    lastIngest: {
                        at: new Date().toISOString(),
                        url,
                        ok: true,
                        job_application_id: ingestData?.job_application_id || null,
                        job_title: jobTitle,
                        company
                    }
                });

                // notify popup (if open)
                chrome.runtime.sendMessage(
                    {
                        type: "APPLYAI_EXTRACT_JD_RESULT",
                        ok: true,
                        url,
                        job_application_id: ingestData?.job_application_id || null,
                        job_title: jobTitle,
                        company
                    },
                    () => void chrome.runtime.lastError
                );

                sendResponse({
                    ok: true,
                    job_application_id: ingestData?.job_application_id || null,
                    job_title: jobTitle,
                    company
                });
                return;
            }

            /**
             * New: Generate Autofill Plan + Apply
             */
            if (message?.type === "APPLYAI_AUTOFILL_PLAN") {
                const progress = (stage) => {
                    chrome.runtime.sendMessage({ type: "APPLYAI_AUTOFILL_PROGRESS", stage }, () => {
                        void chrome.runtime.lastError;
                    });
                };

                console.log("ApplyAI: autofill plan request received", message);
                progress("starting");

                const { extensionToken, lastIngest } = await storageGet(["extensionToken", "lastIngest"]);
                console.log("ApplyAI: storage state", {
                    hasToken: Boolean(extensionToken),
                    lastIngest
                });
                if (!extensionToken) {
                    sendResponse({ ok: false, error: "Not connected. Please connect first." });
                    return;
                }

                const jobApplicationId = message?.job_application_id || lastIngest?.job_application_id;
                if (!jobApplicationId) {
                    sendResponse({ ok: false, error: "Missing job application ID. Extract a job description first." });
                    return;
                }
                console.log("ApplyAI: jobApplicationId", jobApplicationId);

                const tab = await getActiveTab();
                if (!tab?.id) {
                    sendResponse({ ok: false, error: "No active tab found." });
                    return;
                }

                const tabUrl = tab.url || "";
                console.log("ApplyAI: active tab", { tabId: tab.id, tabUrl });
                if (isRestrictedUrl(tabUrl)) {
                    sendResponse({ ok: false, error: "Cannot access this page." });
                    return;
                }

                progress("extracting_dom");

                let { url, dom_html } = await extractDomHtmlFromTab(tab.id);
                if (!url) url = tabUrl;
                if (!dom_html) dom_html = "";
                console.log("ApplyAI: DOM extracted", {
                    url,
                    domLength: dom_html.length
                });

                const MAX_HTML_CHARS = 2_500_000;
                if (dom_html.length > MAX_HTML_CHARS) {
                    sendResponse({ ok: false, error: "Page is too large to process for autofill." });
                    return;
                }

                progress("extracting_fields");

                const formFields = await extractFormFieldsFromTab(tab.id);
                console.log("ApplyAI: Form fields extracted", {
                    fieldCount: formFields.length
                });

                if (!formFields || formFields.length === 0) {
                    sendResponse({ ok: false, error: "No form fields found on this page." });
                    return;
                }

                progress("planning");

                const planRes = await fetch(`${API_BASE_URL}/extension/autofill/plan`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${extensionToken}`
                    },
                    body: JSON.stringify({
                        job_application_id: jobApplicationId,
                        page_url: url,
                        dom_html,
                        extracted_fields: formFields
                    })
                });
                console.log("ApplyAI: plan response status", planRes.status);

                if (planRes.status === 401) {
                    await storageSet({ extensionToken: null });
                    sendResponse({ ok: false, error: "Session expired. Please connect again." });
                    return;
                }

                if (!planRes.ok) {
                    const text = await planRes.text().catch(() => "");
                    sendResponse({ ok: false, error: `Autofill plan failed: ${planRes.status} ${text}` });
                    return;
                }

                const planData = await planRes.json().catch(() => ({}));
                const planJson = planData?.plan_json;
                const planFields = Array.isArray(planJson?.fields) ? planJson.fields : [];
                const actionCounts = planFields.reduce(
                    (acc, field) => {
                        const action = field?.action || "unknown";
                        acc[action] = (acc[action] || 0) + 1;
                        return acc;
                    },
                    {}
                );
                console.log("ApplyAI: plan payload", {
                    run_id: planData?.run_id || null,
                    status: planData?.status || null,
                    totalFields: planFields.length,
                    actionCounts,
                    plan_summary: planData?.plan_summary || null
                });

                // Log event: plan received
                if (planData?.run_id) {
                    logAutofillEvent(planData.run_id, "autofill_plan_received", {
                        field_count: planFields.length,
                        action_counts: actionCounts,
                        status: planData?.status
                    });
                }

                if (!planJson) {
                    sendResponse({ ok: false, error: "No autofill plan returned." });
                    return;
                }

                progress("autofilling");

                const applyResult = await applyAutofillPlanToTab(tab.id, planJson, planData?.resume_url);
                console.log("ApplyAI autofill result:", applyResult);
                if (applyResult?.debug) {
                    console.log("ApplyAI autofill debug:", applyResult.debug);
                }

                // Log event: autofill applied
                if (planData?.run_id) {
                    logAutofillEvent(planData.run_id, "autofill_applied", {
                        filled: applyResult?.filled || 0,
                        skipped: applyResult?.skipped || 0,
                        errors: applyResult?.errors || []
                    });
                }

                chrome.runtime.sendMessage(
                    {
                        type: "APPLYAI_AUTOFILL_RESULT",
                        ok: true,
                        run_id: planData?.run_id || null,
                        plan_summary: planData?.plan_summary || null,
                        filled: applyResult?.filled || 0,
                        skipped: applyResult?.skipped || 0,
                        errors: applyResult?.errors || []
                    },
                    () => void chrome.runtime.lastError
                );

                sendResponse({
                    ok: true,
                    run_id: planData?.run_id || null,
                    filled: applyResult?.filled || 0,
                    skipped: applyResult?.skipped || 0
                });
                return;
            }

            /**
             * Mark application as applied
             */
            if (message?.type === "APPLYAI_MARK_APPLIED" && message?.run_id) {
                const { extensionToken } = await storageGet(["extensionToken"]);
                if (!extensionToken) {
                    sendResponse({ ok: false, error: "Not connected. Please connect first." });
                    return;
                }

                const res = await fetch(`${API_BASE_URL}/extension/autofill/submit`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${extensionToken}`
                    },
                    body: JSON.stringify({
                        run_id: message.run_id,
                        payload: { marked_at: new Date().toISOString() }
                    })
                });

                if (!res.ok) {
                    const text = await res.text().catch(() => "");
                    throw new Error(`Failed to mark as applied: ${res.status} ${text}`);
                }

                // Notify popup of success
                chrome.runtime.sendMessage(
                    { type: "APPLYAI_MARK_APPLIED_RESULT", ok: true },
                    () => void chrome.runtime.lastError
                );

                sendResponse({ ok: true });
                return;
            }

            // default: ignore
            sendResponse({ ok: false, error: "Ignoring message (unknown type)." });
        } catch (err) {
            const msg = String(err?.message || err);

            // persist last failure (not used by popup now, but kept for debugging)
            try {
                await storageSet({
                    lastIngest: {
                        at: new Date().toISOString(),
                        ok: false,
                        reason: msg
                    }
                });
            } catch (_) { }

            let errorMessageType = "APPLYAI_EXTRACT_JD_RESULT";
            if (message?.type === "APPLYAI_AUTOFILL_PLAN") {
                errorMessageType = "APPLYAI_AUTOFILL_RESULT";
            } else if (message?.type === "APPLYAI_MARK_APPLIED") {
                errorMessageType = "APPLYAI_MARK_APPLIED_RESULT";
            }

            chrome.runtime.sendMessage(
                { type: errorMessageType, ok: false, error: msg },
                () => void chrome.runtime.lastError
            );

            sendResponse({ ok: false, error: msg });
        }
    })();

    return true; // keep channel open for async sendResponse
});
