var dayOfWeek = new Date().getDay();
function loadTimeTable(rouId) {
    stopInVar = {};
    pathInVar = {};
    var options = {};
    options.url = "{0}/businfo/gettimetablebyroute/{1}".format(API_URL, rouId);
    options.type = "GET";
    options.success = function (data) {
        if (data != null && data.length) {
            var result = "", id = "", tempVar = "<h3>{0}</h3><div><div>{2}</div><div id='{1}'></div></div>";
            $.each(data, function (key, item) {
                id = "rId{0}tId{1}".format(item.RouteId, item.TimeTableId);
                var applytime = item.StartDate;
                if (item.EndDate != null && item.EndDate != '')
                    applytime = '{0} - {1}'.format(item.StartDate, item.EndDate);
                result += tempVar.format(RES_TIMETABLE_TITLE.format(item.RouteVarShortName, getApplyDatesLocalize(item.ApplyDates), applytime), id, formatTimeTableResult(item));
                AjaxGetTrips(item.RouteId, item.TimeTableId, id);
            });
            $("#accTimetable").html(result);
            $("#accTimetable").accordion({});
        }
        else {
            $("#accTimetable").html(RES_NO_DATA);
        }
    };
    options.error = function (jqXHR, textStatus, err) {
        $("#accordion").html(RES_NO_DATA);
    };
    $.ajax(options);
}

function getApplyDatesLocalize(s) {    
    var result = s;
    result = result.replace('CN', RES_CN);
    result = result.replace('T2', RES_T2);
    result = result.replace('T3', RES_T3);
    result = result.replace('T4', RES_T4);
    result = result.replace('T5', RES_T5);
    result = result.replace('T6', RES_T6);
    result = result.replace('T7', RES_T7);
    
    return result;
}

function formatTimeTableResult(item) {
    var apply = getApplyDatesLocalize(item.ApplyDates);

    var varTimeTableResult = "<table style='align:left'>"
   + "<tr><td style='height:18px;'>{0}</td></tr>".format(RES_ROU_TRIPS.format(item.TotalTrip))
   + "<tr><td style='height:18px'>{0}</td></tr>".format(RES_ROU_TRIP_TIME.format(item.RunningTime))
   + "<tr><td style='height:18px'>{0}</td></tr>".format(RES_ROU_TIME.format(item.OperationTime))
   + "<tr><td style='height:5px'></td></tr>"
   + "<tr><td style='height:18px'>{0}</td></tr>".format(RES_TIMETABLE_FOR.format(apply))
   + "<tr><td style='height:18px'>{0}</td></tr>".format(RES_APPLY_FROM_DATE.format(item.StartDate))
   + "</table>";
    return varTimeTableResult;
}

var varResult = "<tr><td class='orderNo'><div>{0}</div></td><td class='time'>{1} - {2}</td></tr>"

function formatRowResult(item, order) {
    return varResult.format(order, item.StartTime, item.EndTime);
}
function AjaxGetTrips(routeId, timetableId, parentId) {
    var options = {};
    options.url = API_URL + '/businfo/gettripsbytimetable/{0}/{1}'.format(routeId, timetableId);
    options.type = "GET";
    options.success = function (data) {
        if (data != null) {
            var container = "<table cellpadding='0' cellspacing='0'>{0}</table>", result = '';
            var i = 0;
            $.each(data, function (key, item) {
                i = i + 1;
                result = result + formatRowResult(item, i);
            });
            result = container.format(result);
            $('#{0}'.format(parentId)).html(result);
        }
    };
    options.error = function (jqXHR, textStatus, err) {
        $("#divMsg").html(err);
    };
    $.ajax(options);
}