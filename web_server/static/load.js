var offset = topic_count;
var butt = $('#load-button');
// console.log('test');
butt.click(function () {
    // console.log('click');
    butt.text('Loading...');
    butt.addClass('w3-disabled');
    $.ajax({
        dataType: "json",
        url: '/api/' + aggr + '/' + offset.toString(),
        success: function (data) {
            console.log(data);
            $('#view').append(data['data']);
            offset = offset + 5;
            butt.text('Load more');
            butt.removeClass('w3-disabled');
        },
        error: function (data) {
            butt.css('display', 'none');
        }
    });   
});