// fusion360 api

const DEBUG = false;

document.addEventListener("DOMContentLoaded", () => {
    let adskWaiter = setInterval(() => {
        dumpLog("DOMContentLoaded");
        if (window.adsk) {
            dumpLog("adsk ok");
            clearInterval(adskWaiter);

            adsk
            .fusionSendData("DOMContentLoaded", "{}")
            .then((data) => {
                dumpLog(data)
                let info = JSON.parse(data);
                button_addEventListener()
                // lock_addEventListener()
                set_correction_value(info["correction"])
                correction_addEventListener()
            });
        }
    }, 100);
});

// window.fusionJavaScriptHandler = {
//     handle: function (action, data) {
//         try {
//             if (action === "command_event") {
//                 dumpLog("call command_event")
//                 let values = JSON.parse(data);
//                 dumpLog(values['value']);
//                 setDisabledByButton(toBoolean(values["value"]), "button");
//                 setDisabledById(toBoolean(values["value"]), SCOPE_SWITCH_ID);
//                 const sw = document.getElementById(SCOPE_SWITCH_ID);
//                 const chi = document.getElementById(SCOPE_CHILDREN_ID);
//                 if (sw.disabled) {
//                     chi.disabled = true;
//                 } else {
//                     if (sw.checked) {
//                         chi.disabled = false;
//                     } else {
//                         chi.disabled = true;
//                     };
//                 };
//             } else if (action === "debugger") {
//                 debugger;
//             } else {
//                 return `Unexpected command type: ${action}`;
//             }
//         } catch (e) {
//             console.log(e);
//             console.log(`Exception caught with command: ${action}, data: ${data}`);
//         }
//         return "OK";
//     },
// };


function button_addEventListener() {
    let btns = document.getElementsByClassName("btn btn-border");
    let btn_array = Array.prototype.slice.call(btns);
    btn_array.forEach((btn, _) => {
        btn.addEventListener('click',() => {
            let args = {
                value: btn.text
            };
            dumpLog(btn.text);
            adsk.fusionSendData('btn-click', JSON.stringify(args));
        });
    });
}


function correction_addEventListener() {
    let correction = document.getElementById("correction");
    correction.addEventListener('change',() => {
        let args = {
            value: correction.value
        };
        dumpLog(correction.value);

        adsk.fusionSendData('correction-change', JSON.stringify(args)).then((data) => {
            let values = JSON.parse(data);
            let msg = values["value"];
            // let msg = data["value"];
            dumpLog(msg);
            setMessage(msg)
            if (msg.length > 0) {
                let tt = 1;
            }
        });

        let jj = 0;
    });
}


function setMessage(txt) {
    let ele = document.getElementById("error-msg");
    ele.innerText = txt;
}


function set_correction_value(value) {
    let correction = document.getElementById("correction");
    correction.value = value;
}


function lock_addEventListener() {
    let lock = document.getElementById("lock");
    lock.addEventListener('change',() => {
        let args = {
            value: lock.checked
        };
        dumpLog(lock.checked);
        adsk.fusionSendData('lock-change', JSON.stringify(args));
    });
}

function dumpLog(msg) {
    if (DEBUG) {
        console.log(msg);
    };
};