var _thunder_id_ = 37361;
var SHARE = {};

SHARE.ParseTpl = function(str, data) {
  var tplEngine = function(tpl, data) {
    var reg = /\{([^|}]+)?\}/g,
        regOut = /(^( )?(if|for|else|switch|case|break|{|}))(.*)?/g, 
        code = 'var r=[];\n', 
        cursor = 0;

    var add = function(line, js) {
        js? (code += line.match(regOut) ? line + '\n' : 'typeof '+line+'=="undefined"||'+line+'=="null"||typeof '+line+'=="object"?"":r.push('+line+');\n') :
            (code += line != '' ? 'r.push("' + line.replace(/"/g, '\\"') + '");\n' : '');
        return add;
    }
    while(match = reg.exec(tpl)) {
        add(tpl.slice(cursor, match.index))(match[1], true);
        cursor = match.index + match[0].length;
    }
    add(tpl.substr(cursor, tpl.length - cursor));
    code += 'return r.join("");';
    return new Function('data',code.replace(/[\r\t\n]/g, '')).call(this,data);
  }
  //获取元素
  var element = document.getElementById(str);
  if (element) {
      var html = /^(textarea|input)$/i.test(element.nodeName) ? element.value : element.innerHTML;
      return tplEngine(html, data);
  } else {
      return tplEngine(str, data);
  }
}

SHARE.FloatMiddel = function($obj,width,height){
  if(typeof width=='undefined') width = 0;
  if(typeof height=='undefined') height = 0;
  var h_width = width!=''?width:$obj.outerWidth();
  var h_height = height!=''?height:$obj.outerHeight();
  var w_width = $(window).width();
  var w_height = $(window).height();

  $obj.css({'position':'absolute','right':(w_width-h_width)/2,'top':(w_height-h_height)/2+$(document).scrollTop()});
}

SHARE.ThunderEncode = function(url){
  var thunderPrefix="AA";
  var thunderPosix="ZZ";
  var thunderTitle="thunder://";
  var thunderUrl=thunderTitle+Base64.encodeURI(thunderPrefix+url+thunderPosix);
  return thunderUrl;
}

SHARE.TimeOut = function($obj,expire_time){
  var timefunc = function(expire_time){
    var now = Math.round((new Date().getTime())/1000);
    var dist = expire_time-now;
    if(dist<0) return;
    var day = Math.floor(dist/60/60/24);
    var hour = Math.floor(dist/60/60-day*24);
    var min = Math.floor(dist/60-hour*60-day*24*60);
    var sec = Math.floor(dist-min*60-hour*60*60-day*24*60*60);
    var html = '<span class="corner count">'+day+'</span>天<span class="corner count">'+hour+'</span>时<span class="corner count">'+min+'</span>分<span class="corner count">'+sec+'</span>秒';
    $obj.html(html);
    window.setTimeout(timefunc,1000,expire_time);
  }
  timefunc(expire_time);
}

SHARE.Copy=function($obj,string){
  var flash_copy = false;
  var copy_success = function(){ alert('已复制到粘贴板中',1); }
  var text_default = '对不起,没有可复制的内容';
  try{
    if(document.queryCommandSupported('Copy')){
      $obj.click(function(){
        var text = document.createElement('textarea');
        text.value = typeof string=='string'?string:string.call(this);
        if(!text.value){
          alert(text_default);return false;
        };
        text.style.width = 1;
        text.style.height = 1;
        $obj.after(text);
        text.focus();text.select();
        document.execCommand('Copy',false,null);
        $('textarea').remove();
        copy_success();
      })
    }else{
      flash_copy = true;
    }
  }catch(e){
    flash_copy = true;
  }
  if(flash_copy){
    var flush_copy_func = function(){
      $obj.mouseenter(function(){
        var _text = typeof string=='string'?string:string.call(this);
        if(_text){
          ZeroClipboard.setMoviePath(GLOBAL.CONST.RES_URL+'ZeroClipboard10.swf');
          clip = new ZeroClipboard.Client();
          clip.glue($(this).get(0));
          clip.addEventListener('complete',copy_success);
          clip.addEventListener('mouseout',function(client){
            client.hide();
          });
          clip.setText(_text);
        }else{
          $(this).one('click',function(){
            alert(text_default);
          })
        }
      });
    }
    if(typeof ZeroClipboard!='object'){
      $.ajax({url:GLOBAL.CONST.RES_URL+'js/ZeroClipboard.js',type:'get',async:false,dataType:'script',success:function(){flush_copy_func()}})
    }else{
      flush_copy_func();
    }
  }
}

SHARE.item_app_download = function($obj){
  $('.pop_app_down').remove();
  var html = '<div class="pop_app_down"> <div class="tit"> <span class="fl">请选择:</span> <span class="fr"><a>关闭</a></span> </div> <a class="link">点击链接直接下载(已安装客户端)</a> <a class="link" style="z-index:999">复制链接到播放器手动下载</a> <a class="link" target="_blank" href="http://app.zimuzu.tv/YYetsShare.exe">点击下载安装人人播放器客户端</a> <div class="desc">安装人人播放器客户端获得最新最快的影视资讯信息,支持稳定的离线缓存下载,解决资源被网盘和迅雷被和谐的痛点</div> </div>';
  $obj.parent().css({position:'relative',left:0,top:0}).append(html).find('.pop_app_down').css({position:'absolute',top:'25px',left:0}).find('span.fr').click(function(){
    $(this).parents('.pop_app_down').remove();
  }).end().find('.link:first').attr({href:$obj.data('url'),target:'_blank'}).next().mouseenter(function(){
    SHARE.Copy($(this),$obj.data('url'));
  })
}

var share_page_init = function(share_list){
  if(share_list==1 && $('.media-child-item')){/*列表页*/
    var pop_tpl = '<div class="pop-box">\
        <div class="pop-main">\
            <a class="corner pop-close">关闭</a>\
            <div class="pop-tit"><span class="type">{data.format}</span> {data.name} {data.size}<span class="time">{data.dateline} 发布</span></div>\
            <div class="pop-con">\
                <ul class="clearfix tc d-links">{data.thunder}{data.ed2k}{data.magnet}{data.webdisk}{data.ct}{data.xiaomi}</ul>\
            </div>\
        </div>\
    </div>';

    $('.res-item a.down').click(function(){
      var data = [];
      var $parent = $(this).parents('dd');
      var itemid = $parent.attr('itemid');
      data.name = $parent.find('p:first').text();
      data.size = $parent.find('span.fl').text();
      data.dateline = $parent.attr('dateline');
      data.format = $parent.parent().attr('format');
      if(typeof file_list[itemid]=='object'){
        if(file_list[itemid][1]){
          data.ed2k = '<li><a href="'+file_list[itemid][1]+'" target="_blank" class="dl corner">电驴下载</a><br><a class="cp" style="display:none;">[复制源链接]</a></li>';
          data.thunder = '<li><a oncontextmenu="ThunderNetwork_SetHref(this)" class="xl corner" onclick="return OnDownloadClick_Simple(this,2,4);" thunderrestitle="'+data.name+'" thundertype="" thunderpid="'+_thunder_id_+'" thunderhref="'+SHARE.ThunderEncode(file_list[itemid][1])+'">迅雷</a></li>';
          data.xiaomi = '<li><a target="_blank" href="https://d.miwifi.com/d2r/?url='+Base64.encodeURI(file_list[itemid][1])+'&src=yyets&name='+encodeURIComponent(data.name)+'" class="xm corner">小米路由器远程离线下载</a></li>';
        }
        if(file_list[itemid][2]){
          data.magnet = '<li><a href="'+file_list[itemid][2]+'" target="_blank" class="zl corner">磁力下载</a><br><a class="cp" style="display:none;">[复制源链接]</a></li>';
        }
        if(file_list[itemid][9]){
          data.webdisk = '<li><a href="'+file_list[itemid][9]+'" target="_blank" class="wp corner">网盘下载</a><br><a class="cp" style="display:none;">[复制源链接]</a></li>';
        }
        if(file_list[itemid][12]){
          data.ct = '<li><a href="'+file_list[itemid][12]+'" target="_blank" class="wp corner">诚通网盘</a><br><a class="cp" style="display:none;">[复制源链接]</a></li>';
        }
      }

      $('div.w').append(SHARE.ParseTpl(pop_tpl,data));
      if(!is_mobile){
        $('.pop-box a.cp').show().each(function(){
          $(this).mouseenter(function(){
            var share_text = $(this).siblings('a').attr('href');
            SHARE.Copy($(this),share_text);
          })
        });
      }
      SHARE.FloatMiddel($('.pop-box'));
      $('.pop-box').find('a.pop-close').click(function(){
        $('.pop-box').remove()
      })
    });

    $('.res-item[format=APP] dd').each(function(){
      var itemid = $(this).attr('itemid');
      if(typeof file_list[itemid]!='object') return;
      var html = '';
      var play_key = {103:'Acfun',104:'Bilibili',102:'百度云',106:'搜狐',108:'腾讯',107:'乐视',105:'优酷',114:'范特西视频'};
      for(k in play_key){
        if(file_list[itemid][k]) html += '<a href="'+file_list[itemid][k]+'" target="_blank" class="online fl corner">'+play_key[k]+(k==102&&file_list[itemid]['baidu_pwd']?'|密码:'+file_list[itemid]['baidu_pwd']:'')+'</a>'; 
      }
      $(this).append(html);
    })

    $(document).ready(function(){
      SHARE.TimeOut($('.timeout'),expire_time);
    });
  }
}

/*
$(document).ready(function(){
  if(!is_mobile){
    SHARE.Copy($('a.btn-copy'),share_prefix+'的全部资源下载 '+share_url+' 一天后删除,要看的抓紧时间 —— 来自最帅的资源信息分享站');
    $('.res-item .link').show().find('a').each(function(){
      SHARE.Copy($(this),function(){
        var type = $(this).attr('rel');
        var share_text = '',files = [];
        var $obj = $(this).parent().siblings('dd');
        var type_way = {'ed2k':'1','magnet':'2','disk':'9','ct':'12'};
        $obj.each(function(){
          var itemid = $(this).attr('itemid');
          if(typeof file_list[itemid]=='object' && file_list[itemid][type_way[type]]){
            files.push(file_list[itemid][type_way[type]]);
          }
        })
        return files.join('\r\n');
      });
    })
    $('.rrdownload').click(function(){ SHARE.item_app_download($(this)); });
  }
});
*/