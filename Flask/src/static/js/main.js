

function validateCountry() {
    const countryBox = document.querySelector("#countryBox");
    const countryId = countryBox.value;
    return /^\d+$/.test(countryId);
}
function validateStartDate() {
    const startDateBox = document.querySelector("#startDate");
    const startDate = new Date(startDateBox.value + "T00:00:00");
    const dateNow = new Date();
    dateNow.setHours(0, 0, 0, 0);
    const msg = startDate < dateNow ? "Start date can't be in the past." : "";
    startDateBox.setCustomValidity(msg);
    validateEndDate();
}

function validateEndDate() {
    const startDateBox = document.querySelector("#startDate");
    const endDateBox = document.querySelector("#endDate");
    const startDate = new Date(startDateBox.value + "T00:00:00");
    const endDate = new Date(endDateBox.value + "T00:00:00");
    const msg = endDate < startDate ? "End date can't be before start date." : "";
    endDateBox.setCustomValidity(msg);
}

// Add / Edit vacation form validation
function validateVacationForm(event) {
    event.preventDefault();
    validateStartDate();
    if (!validateCountry()) {
        showModal({
            title: '<i class="fa-solid fa-triangle-exclamation"></i>',
            text: "Please choose a country"
        });
        return;
    }
    validateForm(event);
}

// Validate any form
function validateForm(event) {
    if (event.target.reportValidity()) {
        event.target.submit();
    }
}

// Show image
function displayImage() {
    // Image to preview loaded file
    const preview = document.querySelector("#preview");
    // Get loaded file
    const file = document.querySelector('input[type="file"]').files[0];
    // Create FileReader
    const reader = new FileReader();
    // Preview loaded image
    reader.onload = () => {
        preview.src = reader.result;
    }
    // If file loaded and it image - preview it.
    if (file && /^image\/\w+$/.test(file.type)) {
        reader.readAsDataURL(file);
        // Change "Add button text"
        document.querySelector("#imgBtnTxt").innerText = "Change image";
    }
}

// Modal window creation
function showModal(props) {
    const cancelBtnText = props.cancelBtnText || "Cancel";
    const showCancelBtn = props.showCancelBtn;
    const cancelBtn = showCancelBtn ? `<button type="button" class="btn btn-dark" id="cancel">${cancelBtnText}</button>` : "";
    const okBtnText = props.okBtnText || "Ok";
    document.body.insertAdjacentHTML("afterend", `
    <div class="modal fade show" id="staticBackdropLive" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="staticBackdropLiveLabel" style="display: block;" aria-modal="true" role="dialog">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title" id="staticBackdropLabel">${props.title}</h1>
                </div>
                <div class="modal-body">
                    ${props.text}
                </div>
                <div class="modal-footer">
                    ${cancelBtn}
                    <button type="button" class="btn btn-dark" id="ok">${okBtnText}</button>
                </div>
            </div>
        </div>
    </div>`);
    // Add handlers for modal window
    const closeBtnId = showCancelBtn ? "cancel" : "ok";
    document.getElementById(closeBtnId).onclick = () => {
        // Remove modal window
        document.querySelector(".modal").remove();
        document.body.style.overflow = "auto";
    };
    if (showCancelBtn) {
        document.getElementById("ok").onclick = props.okBtnAction;
    }
    // Hide scrolling bar
    document.body.style.overflow = "hidden";
}

// Handle "delete" button click 
function deleteVacation(form) {
    // Show modal window
    showModal({
        title: '<i class="fa-solid fa-triangle-exclamation"></i>',
        text: "Are you really want to delete this vacation?",
        showCancelBtn: true,
        cancelBtnText: "No",
        okBtnText: "Yes",
        okBtnAction: () => {
            form.submit();
        }
    });
    // Add handlers for modal window
    document.getElementById("cancel").onclick = () => {
        // Remove modal window
        document.querySelector(".modal").remove();
        document.body.style.overflow = "auto";
    };
}

// Country selection
function selectCountry(name, id) {
    document.querySelector("#countryBox").value = id;
    document.querySelector("#countrySelector").innerText = name;
    // Set country validity
    validateCountry()
}

window.onload = () => {
    const priceBox = document.getElementById("priceBox");
    if (priceBox) {
        if (priceBox.value) {
            priceBox.value = parseFloat(priceBox.value).toFixed(2);
        }
        priceBox.onblur = () => {
            if (priceBox.value) {
                priceBox.value = parseFloat(priceBox.value).toFixed(2);
            }
        };
    }
    const form = document.querySelector("#vacationForm");
    if (form) {
        const startDateBox = document.querySelector("#startDate");
        const endDateBox = document.querySelector("#endDate");

        startDateBox.addEventListener("change", validateStartDate);
        endDateBox.addEventListener("change", validateEndDate);

        form.addEventListener("submit", validateVacationForm);

        validateStartDate();
    }
};
