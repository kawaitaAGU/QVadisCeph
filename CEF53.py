# z01_2.py — iPhone 対応版（最小修正：三角は動く・ページはスクロールしない・2本指拡大OK）

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base

SD_BASE = 4.0
POLY_WIDTH_SCALE = 2.0
ANGLE_STACK_BASE_WIDTH = 900

ANGLE_STACK_CONFIG = [
    {"id": "Facial", "label": "Facial", "type": "angle", "vectors": [["Pog", "N"], ["Po", "Or"]]},
    {"id": "Convexity", "label": "Convexity", "type": "angle", "vectors": [["N", "A"], ["Pog", "A"]]},
    {"id": "FH_mandiblar", "label": "FH mandiblar", "type": "angle", "vectors": [["Or", "Po"], ["Me", "Am"]]},
    {"id": "Gonial_angle", "label": "Gonial angle", "type": "angle", "vectors": [["Ar", "Pm"], ["Me", "Am"]]},
    {"id": "Ramus_angle", "label": "Ramus angle", "type": "angle", "vectors": [["Ar", "Pm"], ["N", "S"]]},
    {"id": "SNP", "label": "SNP", "type": "angle", "vectors": [["N", "Pog"], ["N", "S"]]},
    {"id": "SNA", "label": "SNA", "type": "angle", "vectors": [["N", "A"], ["N", "S"]]},
    {"id": "SNB", "label": "SNB", "type": "angle", "vectors": [["N", "B"], ["N", "S"]]},
    {"id": "SNA-SNB diff", "label": "SNA - SNB", "type": "difference", "minuend": "SNA", "subtrahend": "SNB"},
    {"id": "Interincisal", "label": "Interincisal", "type": "angle", "vectors": [["U1", "U1r"], ["L1", "L1r"]]},
    {"id": "U1 to FH plane", "label": "U1 - FH plane", "type": "angle", "vectors": [["U1", "U1r"], ["Po", "Or"]]},
    {"id": "L1 to Mandibular", "label": "L1 - Mandibular", "type": "angle", "vectors": [["Me", "Am"], ["L1", "L1r"]]},
    {"id": "L1_FH", "label": "L1 - FH", "type": "angle", "vectors": [["L1", "L1r"], ["Or", "Po"]]},
]

POLYGON_ROWS = [
    ["VTOP", 0.0, 0.0, 0.0],
    ["00", 0.0, 0.0, 0.0],
    ["Facial", 83.1, 2.5, 0.1036],
    ["Convexity", 11.3, 4.6, 0.1607],
    ["FH_mandiblar", 32.0, 2.4, 0.0893],
    ["Gonial_angle", 129.2, 4.7, 0.1786],
    ["Ramus_angle", 89.7, 3.7, 0.1429],
    ["SNP", 76.1, 2.8, 0.1250],
    ["SNA", 80.9, 3.1, 0.1250],
    ["SNB", 76.2, 2.8, 0.1286],
    ["SNA-SNB diff", 4.7, 1.8, 0.0714],
    ["01", 0.0, 0.0, 0.0],
    ["Interincisal", 124.3, 6.9, 0.2500],
    ["U1 to FH plane", 109.8, 5.3, 0.1679],
    ["L1 to Mandibular", 93.8, 5.9, 0.2107],
    ["L1_FH", 57.2, 3.9, 0.2500],
    ["ZZ", 0.0, 0.0, 0.0],
    ["VBOT", 0.0, 0.0, 0.0],
]


def render_ceph_component(image_data_url: str, marker_size: int, show_labels: bool, point_state: dict):
    payload_json = base.build_component_payload(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=point_state,
    )

    angle_rows_html = "".join(
        f'<div class="angle-row" data-angle="{cfg["id"]}">'
        f'  <span class="angle-name">{cfg["label"]}</span>'
        f'  <span class="angle-value">--.-°</span>'
        f'</div>'
        for cfg in ANGLE_STACK_CONFIG
    )

    html = """
    <style>
      .ceph-wrapper{
        position:relative;width:min(100%,960px);margin:0 auto;
        overscroll-behavior:contain;
      }

      #ceph-image{
        width:100%;height:auto;display:block;
        pointer-events:none;user-select:none;-webkit-user-select:none;
      }

      #ceph-planes,#ceph-overlay{
        position:absolute;inset:0;pointer-events:none;
      }

      #ceph-stage{
        position:absolute;inset:0;pointer-events:auto;
        touch-action:auto; /* ← ここは auto のままなので2本指ピンチは生かされる */
        user-select:none;-webkit-user-select:none;
      }

      /* ▼重要：マーカーの上だけはスクロールやピンチを禁止 */
      .ceph-marker{
        position:absolute;transform:translate(-50%,0);
        cursor:grab;
        touch-action:none;     /* ← iPhoneのスクロールを止めてドラッグ優先 */
      }
      .ceph-marker *{
        touch-action:none;
      }
      /* ▲ */

      .ceph-marker.dragging{cursor:grabbing;}
      .ceph-marker .pin{width:0;height:0;margin:0 auto;}
      .ceph-label{
        margin-top:2px;font-size:11px;font-weight:700;color:#f8fafc;
        text-shadow:0 1px 2px rgba(0,0,0,.6);text-align:center;
      }

      #angle-stack{
        position:absolute;top:56px;left:12px;
        display:flex;flex-direction:column;gap:8px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#f8fafc;
        pointer-events:none;z-index:4;min-width:140px;
        transform-origin:top left;transform:scale(1);
      }
      .angle-row{display:flex;justify-content:space-between;padding:2px 0;}
      .angle-row.dimmed{opacity:.45;}

      #coord-stack{margin-top:8px;font-size:11px;max-height:200px;overflow:auto;}
      #std-poly-outline{fill:none;stroke:#fff;stroke-width:1.6;}
      .std-centerline{stroke:#facc15;stroke-width:2;}
      .std-hline{stroke:#fff;stroke-width:1.1;}
      .std-patient{stroke:#ef4444;stroke-width:2;fill:none;}
    </style>

    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const POLYGON_ROWS = __POLY_ROWS_JSON__;
      const SD_BASE = __SD_BASE__;
      const POLY_WIDTH_SCALE = __POLY_WIDTH_SCALE__;
      const ANGLE_STACK_BASE_WIDTH = __ANGLE_STACK_BASE_WIDTH__;
      const payload = __PAYLOAD_JSON__;

      (function(){
        const wrapper = document.querySelector(".ceph-wrapper");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");
        const angleStack= document.getElementById("angle-stack");
        const coordStack= document.getElementById("coord-stack");

        const markers=[], markerById={};
        let activeMarker=null, dragOffset={x:0,y:0};

        const clamp=(v,lo,hi)=>Math.min(Math.max(v,lo),hi);

        /* ===== マーカー作成 ===== */
        function setPosition(m,left,top){
          const w=stage.clientWidth,h=stage.clientHeight;
          const cl=Math.round(clamp(left,0,w));
          const ct=Math.round(clamp(top,0,h));
          m.style.left=cl+"px"; m.style.top=ct+"px";
          m.dataset.left=cl; m.dataset.top=ct;
        }

        function createMarker(pt){
          const m=document.createElement("div");
          m.className="ceph-marker";
          m.dataset.id=pt.id;

          const s=pt.size||28;
          const pin=document.createElement("div");
          pin.className="pin";
          pin.style.borderLeft=(s/4)+"px solid transparent";
          pin.style.borderRight=(s/4)+"px solid transparent";
          pin.style.borderBottom=s+"px solid "+(pt.color||"#f97316");
          m.appendChild(pin);

          const lbl=document.createElement("div");
          lbl.className="ceph-label";
          lbl.textContent=pt.id;
          m.appendChild(lbl);

          if(pt.x_px!=null){
            m.dataset.left=pt.x_px; m.dataset.top=pt.y_px; m.dataset.initPlaced="1";
          }else{
            m.dataset.ratioX=pt.ratio_x; m.dataset.ratioY=pt.ratio_y;
            m.dataset.initPlaced="0";
          }

          /* pointerdown */
          m.addEventListener("pointerdown",(ev)=>{
            if(ev.pointerType==="touch" && ev.isPrimary){
              ev.preventDefault();  /* ← iPhoneでのスクロール開始を殺す */
            }
            const rect=stage.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0");
            const top =parseFloat(m.dataset.top ||"0");
            dragOffset={x:ev.clientX-(rect.left+left),y:ev.clientY-(rect.top+top)};
            activeMarker=m;
            m.classList.add("dragging");
          });

          /* pointermove */
          m.addEventListener("pointermove",(ev)=>{
            if(activeMarker!==m) return;
            if(ev.pointerType==="touch" && ev.isPrimary){
              ev.preventDefault();  /* ← ドラッグ中スクロール抑止 */
            }
            const rect=stage.getBoundingClientRect();
            setPosition(
              m,
              ev.clientX-rect.left-dragOffset.x,
              ev.clientY-rect.top -dragOffset.y
            );
            updateAll();
          });

          /* pointerup/pointercancel */
          const finish=()=>{
            if(activeMarker===m){
              m.classList.remove("dragging");
              activeMarker=null;
              updateAll();
            }
          };
          m.addEventListener("pointerup",finish);
          m.addEventListener("pointercancel",finish);

          stage.appendChild(m);
          markerById[pt.id]=m;
          markers.push(m);
        }


        /* ===== レイアウト後の初期配置 ===== */
        function placeInitMarkersOnce(){
          const w=stage.clientWidth, h=stage.clientHeight;
          markers.forEach(m=>{
            if(m.dataset.initPlaced==="1"){
              setPosition(m,parseFloat(m.dataset.left),parseFloat(m.dataset.top));
            }else{
              const rx=parseFloat(m.dataset.ratioX||0.5);
              const ry=parseFloat(m.dataset.ratioY||0.5);
              setPosition(m,rx*w,ry*h);
              m.dataset.initPlaced="1";
            }
          });
        }

        /* ===== 全更新 ===== */
        function updateAll(){
          // planes / angle / polygon / coord
        }

        (payload.points||[]).forEach(pt=>createMarker(pt));

        function updateLayout(){
          const w=image.clientWidth,h=image.clientHeight;
          stage.style.width=w+"px";
          stage.style.height=h+"px";
          placeInitMarkersOnce();
          updateAll();
        }

        if(image.complete) updateLayout();
        else image.addEventListener("load",updateLayout,{once:true});

        window.addEventListener("resize",updateLayout);
      })();
    </script>
    """

    html = html.replace("__IMAGE_DATA_URL__", image_data_url)
    html = html.replace("__ANGLE_ROWS_HTML__", angle_rows_html)
    html = html.replace("__ANGLE_CONFIG_JSON__", json.dumps(ANGLE_STACK_CONFIG))
    html = html.replace("__POLY_ROWS_JSON__", json.dumps(POLYGON_ROWS))
    html = html.replace("__SD_BASE__", json.dumps(SD_BASE))
    html = html.replace("__POLY_WIDTH_SCALE__", json.dumps(POLY_WIDTH_SCALE))
    html = html.replace("__ANGLE_STACK_BASE_WIDTH__", json.dumps(ANGLE_STACK_BASE_WIDTH))
    html = html.replace("__PAYLOAD_JSON__", payload_json)

    return components.html(html, height=1100, scrolling=False)



def slim_main():
    base.ensure_session_state()

    st.markdown("### 画像の選択")
    uploaded = st.file_uploader(
        "分析したいレントゲン画像をアップロードしてください。",
        type=["png","jpg","jpeg","gif","webp"]
    )

    if uploaded:
        image_bytes = uploaded.read()
        mime = uploaded.type or "image/png"
        url = base.to_data_url(image_bytes,mime)
        st.session_state.default_image_data_url = url

    url = st.session_state.default_image_data_url
    if not url:
        st.error("画像をアップロードしてください")
        return

    render_ceph_component(
        image_data_url=url,
        marker_size=26,
        show_labels=True,
        point_state=st.session_state.ceph_points
    )


def main():
    slim_main()


if __name__ == "__main__":
    main()
