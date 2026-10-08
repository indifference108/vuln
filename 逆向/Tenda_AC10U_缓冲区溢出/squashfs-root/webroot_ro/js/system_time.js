var G = {};
var initObj = null;

var sysTimeInfo;
var pageview = R.pageView({ //页面初始化
	init: function () {
		top.loginOut();
		top.$(".main-dailog").removeClass("none");
		top.$(".save-msg").addClass("none");
		$("#submit").on("click", function () {
			G.validate.checkAll();
		});
	}
});
var pageModel = R.pageModel({
	getUrl: "goform/GetSysTimeCfg",
	setUrl: "goform/SetSysTimeCfg",
	translateData: function (data) {
		var newData = {};
		newData.sysTime = data;
		return newData;
	},
	afterSubmit: callback
});

/************************/
var view = R.moduleView({
	initEvent: checkData
})
var moduleModel = R.moduleModel({
	initData: initValue,
	getSubmitData: function () {
		var data,
			subObj = {},
            timeZone = $("#timeZone").val();
		var browserLang = getBrowserLang();
        var ruTimeZoneList = ["2:10","3:10","4:10","5:10","6:10","7:10","8:10","9:10","10:10","11:10","12:10","14:10","15:10","16:10","17:10","18:10","19:10","20:10","21:10","22:10","23:10","24:10"];
            for(var i = 0;i++;i < ruTimeZoneList){
                if(timeZone == ruTimeZoneList[i]){
                    timeZone = $("#timeZone").val().split(":")[0]+":00"
                }else {
					timeZone = $("#timeZone").val();
				}
			}
        
		subObj = {
			//"timeType": $("[name='timeType']:checked").val(),
			//"timePeriod": $("#timePeriod").val(initObj.timePeriod),
			//"ntpServer": $("#ntpServer").val(initObj.ntpServer),
			"timePeriod": initObj.timePeriod,
			"ntpServer": initObj.ntpServer,
			"timeZone": timeZone
				//"time": $("#time").val()
		};
		data = objTostring(subObj);
		return data;
	}
});

//模块注册
R.module("sysTime", view, moduleModel);

function checkData() {
	G.validate = $.validate({
		custom: function () {

			/*if ($("#ntpServer").val() == "") {
				$("#ntpServer").focus();
				return _("Please enter a valid NTP server IP address.");
			}
			if (!(/^[ -~]+$/g).test($("#ntpServer").val())) {
				$("#ntpServer").focus();
				return _("Please enter a valid NTP server IP address.");
			}*/
		},
		success: function () {
			sysTimeInfo.submit();
		},

		error: function (msg) {
			if (msg) {
				$("#msg-err").html(msg);
			}
			return;
		}
	});
}

function initValue(obj) {
    var browserLang = getBrowserLang();
	if(B.lang != "ru" && B.lang != "uk"){
        $(".ruTimezone").remove();
    }
	initObj = obj;
	//$("[name='ruTimeType'][value='" + obj.timeZone + "']")[0].checked = true;
    var ruTimeZoneList = ["2:00","3:00","4:00","5:00","6:00","7:00","8:00","9:00","10:00","11:00","12:00",]
    var ruTimeZone = obj.timeZone;
    if(browserLang == "RU" || browserLang == "UK"){
        for(var i = 0;i++;i < ruTimeZoneList){
            if(ruTimeZone == ruTimeZoneList[i]){
                ruTimeZone = obj.timeZone.split(":")[0]+":10"
            }
        }
        $("#timeZone").val(ruTimeZone);
    }else {
	    $("#timeZone").val(obj.timeZone);
    }
    //$("#timeZone").val(obj.timeZone);
	$("#sysTime").text(obj.time);
	if (obj.isSyncInternetTime == "true") {
		$("#syncInternetTips").text(_("(synchronized with internet time)"));
	} else {
		$("#syncInternetTips").text(_("(unsynchronized with internet time)"));
	}
	/*$("#ntpServer").val(obj.ntpServer);
	$("#timePeriod").val(obj.timePeriod);*/
	top.initIframeHeight();
}

function callback(str) {
	if (!top.isTimeout(str)) {
		return;
	}
	var num = $.parseJSON(str).errCode;

	top.showSaveMsg(num);
	if (num == 0) {
		top.advInfo.initValue();
	}
}


window.onload = function () {
	sysTimeInfo = R.page(pageview, pageModel);
};