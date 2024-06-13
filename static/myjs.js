$(document).ready(function () {
    get_posts("{{user_info.username}}");
});
function sign_out() {
    $.removeCookie("mytoken", { path: "/" });
    alert("Signed out!");
    window.location.href = "/login";
}
$(document).ready(function () {
    show_act();
});
function show_act() {
    $('#act-list').empty();
    $.ajax({
        type: "GET",
        url: "/act",
        data: {},
        success: function (response) {
            let rows = response['acts']
            for (let i = 0; i < rows.length; i++) {
                let act = rows[i]['act'];
                let num = rows[i]['num'];
                let done = rows[i]['done'];

                let temp_html = '';
                if (done === 0) {
                    temp_html = `
                    <li>
                        <h2> ${act}</h2>
                        <button onclick="done_act(${num})" type="button" class="btn btn-outline-primary">Done!</button>
                        <button onclick="delete_act(${num})" type="button" class="btn btn-outline-danger btn-delete">Delete</button>
                    </li>
                    `;
                } else {
                    temp_html = `
                    <li>
                        <h2 class="done">✅ ${act}</h2>
                        <button onclick="delete_act(${num})" type="button" class="btn btn-outline-danger btn-delete">Delete</button>
                    </li>
                    `;
                } $('#act-list').append(temp_html);
            }
        }
    });
}
function save_act() {
    let act = $('#act').val();
    $.ajax({
        type: "POST",
        url: "/act",
        data: { act_give: act },
        success: function (response) {
            alert(response["msg"]);
            window.location.reload();
        }
    });
}
function done_act(num) {
    $.ajax({
        type: "POST",
        url: "/act/done",
        data: { num_give: num },
        success: function () {
            window.location.reload();
        }
    });
}
function delete_act(num) {
    $.ajax({
        type: "POST",
        url: "/delete",
        data: { num_give: num },
        success: function (response) {
            alert(response["msg"]);
            show_act();
        }
    });
}