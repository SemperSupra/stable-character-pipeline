package fauna_csv

// Native-layout probe verifies a byte-exact *shape* known from a pinned,
// third-party copied VHDC CSV. It is metadata-only; the caller must independently
// attest rights, bytes and original-host identity before any data admission.
import (
    "bytes"
    "encoding/csv"
    "errors"
    "fmt"
    "io"
    "math"
    "strconv"
)

const NativeCSVSchema = "scp.fauna.vhdc-native-layout-probe.v1"

// These labels are taken from the publicly readable header of
// nomagiclab/kine2go-pipeline commit 65b39f..., Horse1_M1_walk1_kinematics.csv.
// This does NOT authenticate that GitHub copy to the original VHDC host.
var NativeColumns = [23]string{
    "Frame#","Time",
    "HeadX","HeadY","HeadZ",
    "WithersX","WithersY","WithersZ",
    "SacrumX","SacrumY","SacrumZ",
    "HFLX","HFLY","HFLZ",
    "HFRX","HFRY","HFRZ",
    "HHLX","HHLY","HHLZ",
    "HHRX","HHRY","HHRZ",
}

type NativeLayoutProbe struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    DatasetAdmission string `json:"dataset_admission"`
    BytesSHA256 string `json:"bytes_sha256"`
    ReferenceURL string `json:"reference_url"`
    SourceAuthority string `json:"source_authority"`
    Columns [23]string `json:"columns"`
    DataRows int `json:"data_rows"`
    FirstFrame int `json:"first_frame"`
    LastFrame int `json:"last_frame"`
    FirstTimeNumber float64 `json:"first_time_number"`
    LastTimeNumber float64 `json:"last_time_number"`
    MinTimeDeltaNumber float64 `json:"min_time_delta_number"`
    MaxTimeDeltaNumber float64 `json:"max_time_delta_number"`
    LandmarkXYZChannelsPresent bool `json:"landmark_xyz_channels_present"`
    Units string `json:"physical_units"`
    SourceTimeUnit string `json:"source_time_unit"`
    FPS string `json:"native_fps"`
    SourceAxes string `json:"source_axes"`
    RootFrame string `json:"relative_or_global"`
    TruePhysicalContactEstablished bool `json:"true_physical_contact_established"`
    MeasurementOriginIndependentlyAuthenticated bool `json:"measurement_origin_independently_authenticated"`
    OriginalSiteBytesIndependentlyAuthenticated bool `json:"original_site_bytes_independently_authenticated"`
    Unknown []string `json:"unknown"`
}

const copiedReference = "https://github.com/nomagiclab/kine2go-pipeline/blob/65b39f104706c1b4307dfc2a7df2aa8bed8d20aa/motion_retargeting/data/Horse/Horse1_M1_walk1_kinematics.csv"

func ProbeNativeLayout(raw []byte, expectedSHA256 string)(NativeLayoutProbe,error) {
    var zero NativeLayoutProbe
    if len(raw)==0 || len(raw)>MaxBytes {
        return zero,errors.New("source bytes are empty or exceed read-only experiment budget")
    }
    // This is an integrity pin only: the caller may NOT use it as an author,
    // license, recording-lineage, physical-unit or provider attestation.
    if len(expectedSHA256)!=64 || Digest(raw)!=expectedSHA256 {
        return zero,errors.New("independently supplied digest absent or does not match original bytes")
    }
    r:=csv.NewReader(bytes.NewReader(raw))
    r.FieldsPerRecord=len(NativeColumns)
    r.LazyQuotes=false
    r.TrimLeadingSpace=false
    header,err:=r.Read();if err!=nil{return zero,fmt.Errorf("CSV header invalid: %w",err)}
    for n,k:=range NativeColumns {
        if header[n]!=k{return zero,fmt.Errorf("native header channel %d mismatch (refuse synthetic or unknown column order)",n)}
    }

    rows:=0
    firstFrame,lastFrame:=0,0
    var firstTime,lastTime,previousTime,minDelta,maxDelta float64
    minDelta=math.Inf(1)
    for {
        fields,e:=r.Read()
        if errors.Is(e,io.EOF){break}
        if e!=nil{return zero,fmt.Errorf("source CSV row %d: %w",rows+1,e)}
        if rows>=10000{return zero,errors.New("too many input rows")}
        // Native copied source is one-indexed. Do not silently shift it to 0.
        num,e:=strconv.Atoi(fields[0])
        if e!=nil||num<1||(rows>0&&num!=lastFrame+1){
            return zero,errors.New("unknown, duplicated, or omitted source-frame number")
        }
        time,e:=number(fields[1])
        if e!=nil || time<0 || (rows>0&&time<=previousTime) {
            return zero,errors.New("invalid or nonmonotonic source Time column")
        }
        for _,cell:=range fields[2:]{
            value,e:=number(cell)
            if e!=nil||math.Abs(value)>1e9{return zero,errors.New("nonfinite, malformed or unbounded XYZ source number")}
        }
        if rows==0 {firstFrame=num;firstTime=time}
        if rows>0 {
            delta:=time-previousTime
            if delta<minDelta{minDelta=delta}
            if delta>maxDelta{maxDelta=delta}
        }
        rows++;lastFrame=num;lastTime=time;previousTime=time
    }
    if rows<3{return zero,errors.New("insufficient temporal evidence for sampling-interval observation")}
    if math.IsNaN(minDelta)||math.IsInf(minDelta,0)||math.IsNaN(maxDelta)||math.IsInf(maxDelta,0) {
        return zero,errors.New("invalid source interval stats")
    }
    return NativeLayoutProbe{
        Schema:NativeCSVSchema,Status:"PASS_NATIVE_LAYOUT_SHAPE_ONLY",
        DatasetAdmission:"NOT_ADMITTED",
        BytesSHA256:Digest(raw),
        ReferenceURL:copiedReference,
        SourceAuthority:"NOT_ATTESTED_LAYOUT_REFERENCE_ONLY",
        Columns:NativeColumns,
        DataRows:rows,FirstFrame:firstFrame,LastFrame:lastFrame,
        FirstTimeNumber:firstTime,LastTimeNumber:lastTime,
        MinTimeDeltaNumber:minDelta,MaxTimeDeltaNumber:maxDelta,
        LandmarkXYZChannelsPresent:true,
        Units:"UNKNOWN",SourceTimeUnit:"UNKNOWN",FPS:"UNKNOWN",
        SourceAxes:"UNKNOWN",RootFrame:"UNKNOWN",
        TruePhysicalContactEstablished:false,
        MeasurementOriginIndependentlyAuthenticated:false,
        OriginalSiteBytesIndependentlyAuthenticated:false,
        Unknown:[]string{"source_host_byte_equivalence","per_file_original_rights",
            "physical_source_units","time_column_units_and_native_fps",
            "global_or_relative_root_motion","physical_floor_and_true_contact",
            "sensor_observation_provenance","species_anatomy_validity"},
    },nil
}

// Data values are never emitted: the output contains only bounded shape,
// intervals, and the original digest. This is NOT a reusable source-data API.
