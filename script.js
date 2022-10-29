var LOG_INTERVAL_MS = 1000

var data=[];
var t_fps='60';
var t_resolution='1920X1080';
var t_bitrate='40000';
var t_bufferLevel='10';
var saveBtn=document.getElementById("save_btn");

var stallData = [];
var stallStartTime = null
var stallLength = null

function saveDate(filename, text){
    var pom = document.createElement('a');
    pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    pom.setAttribute('download', filename);
    if (document.createEvent) {
        var event = document.createEvent('MouseEvents');
        event.initEvent('click', true, true);
        pom.dispatchEvent(event);
    } else {
        pom.click();
    }
}

function onStalled() {
    stallStartTime = new Date();
};

function onStarted() {
    if (stallStartTime == null) {
        return; } // No stall was started. This might be the first time the stream started. Just ignore.

    var stallStopTime = new Date();

    // Date.getTime converts the datetime to a number of milliseconds since the epoch.
    var timeElapsedMs = stallStopTime.getTime() - stallStartTime.getTime();
    var logMsg = "STALL: " + timeElapsedMs + " ms";
    stallData.push(logMsg);

    var fileName = "Stalls.log";
    var stallDatasStr = stallData.join("\n").toString();
    // In the same way the performance data is logged, each time a new entry is added we "download" a new file with the updated full list of stalls.
    saveDate(fileName, stallDatasStr);

    stallStartTime = null;
};

function onQualityChanged() {

};

saveBtn.onclick=function(){
	var t_data=data.join('')
    var dataString=t_data.toString();
    saveDate("Tester_",dataString);
    // saveBtn.style.display="none";
    //startBtn.style.display="block";s
}

var timer=setTimeout(function(){
	saveBtn.click();
},10000)

<!--setup the video element and attach it to the Dash player-->
function display(){
    var datetime = new Date();
    console.log(datetime)
    //var url = "http://192.168.8.14/manifest_20000ms.mpd?t="+datetime; // Home Dell server
    //var url = "http://130.215.30.14/manifest.mpd?t="+datetime; // Xiaokun's server
    //var url = "http://mlcneta.cs.wpi.edu/manifest_20000ms.mpd?t="+datetime; // MLCNetA server
    var url = "http://localhost/manifest_20000ms.mpd?t="+datetime; // localhost server
    var player = dashjs.MediaPlayer().create();
    player.updateSettings({
        streaming: {
        buffer:{
            bufferToKeep: 20, // Default
            stableBufferTime: 20, // Default: 12
            bufferTimeAtTopQuality: 40, // Default: 30
            fastSwitchEnabled: true, //  Default
            initialBufferLevel: NaN // Default
        }
        }
    });
    
    player.initialize(document.querySelector("#video"), url, true);
    player.on(dashjs.MediaPlayer.events["PLAYBACK_ENDED"], function () {
        clearInterval(eventPoller);
        clearInterval(bitrateCalculator);
    });
    player.on(dashjs.MediaPlayer.events["BUFFER_EMPTY"], onStalled);
    player.on(dashjs.MediaPlayer.events["BUFFER_LOADED"], onStarted);
    player.on(dashjs.MediaPlayer.events["QUALITY_CHANGE_REQUESTED"], onQualityChanged);

    var eventPoller = setInterval(function () {
        var streamInfo = player.getActiveStream().getStreamInfo();
        var dashMetrics = player.getDashMetrics();
        var dashAdapter = player.getDashAdapter();

        if (dashMetrics && streamInfo) {
            const periodIdx = streamInfo.index;
            var repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
            var bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
            var bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
            var adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo);
            var currentRep = adaptation.Representation_asArray.find(function (rep) {
                return rep.id === repSwitch.to
            })
            var frameRate = currentRep.frameRate;
            var resolution = currentRep.width + 'x' + currentRep.height;
            var cur_biterate = player.getAverageThroughput('video', true);

            var t_time=document.getElementById('video').currentTime;



            t_fps=frameRate;
            t_resolution=resolution;
            t_bitrate=bitrate;
            t_bufferLevel=bufferLevel;

            temp_data=t_time+':'+t_fps+','+t_resolution+','+t_bitrate+','+t_bufferLevel+'\n';
            data.push(temp_data);


            document.getElementById('bufferLevel').innerText = bufferLevel + " secs";
            document.getElementById('framerate').innerText = frameRate + " fps";
            document.getElementById('reportedBitrate').innerText = bitrate + " Kbps";
            document.getElementById('resolution').innerText = resolution;
            // document.getElementById('calculatedBitrate').innerText = Math.round(cur_biterate);
        }
    }, LOG_INTERVAL_MS);

    if (video.webkitVideoDecodedByteCount !== undefined) {
        var lastDecodedByteCount = 0;
        const bitrateInterval = 5;
        var bitrateCalculator = setInterval(function () {
            var calculatedBitrate = (((video.webkitVideoDecodedByteCount - lastDecodedByteCount) / 1000) * 8) / bitrateInterval;
            document.getElementById('calculatedBitrate').innerText = Math.round(calculatedBitrate) + " Kbps";
            lastDecodedByteCount = video.webkitVideoDecodedByteCount;
        }, bitrateInterval * 1000);
    } else {
        document.getElementById('chrome-only').style.display = "none";
    }

};