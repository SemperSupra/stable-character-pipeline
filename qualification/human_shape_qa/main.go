// Original synthetic R009 pixel-alpha silhouette oracle. No identity/sex inference.
package main

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "image"
    _ "image/png"
    "math"
    "os"
    "path/filepath"
    "sort"
    "strings"
)

type ImageMeta struct {
    Actor string `json:"actor"`
    View string `json:"view"`
    Name string `json:"name"`
    SHA256 string `json:"sha256"`
    Bytes int `json:"bytes"`
    CameraScale float64 `json:"camera_ortho_scale"`
    Preset string `json:"preset"`
    VisualAccepted bool `json:"visual_anatomy_accepted"`
}
type Index struct {
    Schema string `json:"schema"`
    SourceSHA string `json:"source_sha256"`
    FileCount int `json:"file_count"`
    Images []ImageMeta `json:"images"`
    Pose string `json:"pose"`
    Pixels string `json:"pixels"`
    BlenderVersion string `json:"blender_version"`
    FullBodyAccepted bool `json:"full_body_anatomy_accepted"`
    FaceAccepted bool `json:"face_identity_accepted"`
    CollisionAccepted bool `json:"garment_collision_accepted"`
}
type Rect struct {
    XMin int `json:"x_min"`
    YMin int `json:"y_min"`
    XMax int `json:"x_max"`
    YMax int `json:"y_max"`
}
type Observation struct {
    Actor string `json:"actor"`
    View string `json:"view"`
    ImageSHA string `json:"image_sha256"`
    Width int `json:"image_width"`
    Height int `json:"image_height"`
    AlphaPixels int `json:"alpha_pixels"`
    Coverage float64 `json:"alpha_coverage"`
    Bounds Rect `json:"alpha_bounds"`
    Margins [4]int `json:"margin_ltrb_px"`
    UpperBandWidth int `json:"upper_band_width_px"`
    MiddleBandWidth int `json:"middle_band_width_px"`
    LowerBandWidth int `json:"lower_band_width_px"`
    Result string `json:"result"`
}
type Report struct {
    Schema string `json:"schema"`
    SourceSHA string `json:"source_sha256"`
    Count int `json:"verified_views"`
    Captures []Observation `json:"captures"`
    CropScreen string `json:"crop_screen"`
    AnatomicalAccuracyAccepted bool `json:"anatomical_accuracy_accepted"`
    SexFromImageInferred bool `json:"sex_from_image_inferred"`
    GarmentClearanceAccepted bool `json:"garment_clearance_accepted"`
    FaceIdentityAccepted bool `json:"face_identity_accepted"`
}
func validDigest(s string) bool {
    if len(s)!=64 || strings.ToLower(s)!=s{return false}
    _,err:=hex.DecodeString(s)
    return err==nil
}
func safeName(s string) bool {
    return s!="" && filepath.Base(s)==s && s!="." && s!=".." &&
        !strings.ContainsAny(s,"/\\")
}
func bandWidth(points [][]bool, bottom, top float64, yMin, yMax int) int {
    a:=yMin+int(float64(yMax-yMin)*bottom)
    b:=yMin+int(math.Ceil(float64(yMax-yMin)*top))
    if b<a{b=a}
    min,max:=int(^uint(0)>>1),-1
    for y:=a;y<=b && y<len(points);y++ {
        if y<0 {continue}
        for x,v:=range points[y] {if v {
            if x<min{min=x};if x>max{max=x}
        }}
    }
    if max<min{return 0}
    return max-min+1
}
func inspect(path string, meta ImageMeta) (Observation,error) {
    ob:=Observation{Actor:meta.Actor,View:meta.View,ImageSHA:meta.SHA256}
    if !safeName(meta.Name) || !strings.HasSuffix(meta.Name,".png") {
        return ob,errors.New("UNSAFE_IMAGE_NAME")
    }
    raw,err:=os.ReadFile(path)
    if err!=nil{return ob,err}
    sha:=sha256.Sum256(raw)
    if hex.EncodeToString(sha[:])!=meta.SHA256 || len(raw)!=meta.Bytes {
        return ob,errors.New("PNG_BYTES_OR_DIGEST_MISMATCH")
    }
    f,err:=os.Open(path)
    if err!=nil{return ob,err}
    defer f.Close()
    im,format,err:=image.Decode(f)
    if err!=nil || format!="png"{return ob,errors.New("INVALID_PNG")}
    rect:=im.Bounds();w,h:=rect.Dx(),rect.Dy()
    if w!=768 || h!=768{return ob,errors.New("CAMERA_RESOLUTION_MISMATCH")}
    ob.Width=w;ob.Height=h
    minx,miny,maxx,maxy:=w,h,-1,-1
    mask:=make([][]bool,h)
    opaque,transparent:=0,0
    for y:=0;y<h;y++ {
        mask[y]=make([]bool,w)
        for x:=0;x<w;x++ {
            _,_,_,alpha:=im.At(x+rect.Min.X,y+rect.Min.Y).RGBA()
            if alpha>=65500 {opaque++}
            if alpha<=1024 {transparent++}
            if alpha>1024 {
                mask[y][x]=true
                ob.AlphaPixels++
                if x<minx{minx=x};if x>maxx{maxx=x}
                if y<miny{miny=y};if y>maxy{maxy=y}
            }
        }
    }
    if opaque==w*h || transparent==0{return ob,errors.New("ALPHA_BACKGROUND_MISSING")}
    if maxx<0{return ob,errors.New("BLANK_SILHOUETTE")}
    ob.Coverage=float64(ob.AlphaPixels)/float64(w*h)
    if ob.Coverage<0.01 || ob.Coverage>0.80{return ob,errors.New("SILHOUETTE_COVERAGE_OUT_OF_RANGE")}
    ob.Bounds=Rect{minx,miny,maxx,maxy}
    ob.Margins=[4]int{minx,miny,w-1-maxx,h-1-maxy}
    // Face captures intentionally crop the torso below the neck. For them,
    // only the upper/side bounds are framing gates; the bottom is an
    // intentional close-up boundary and cannot be called a full-body pass.
    if meta.View=="face" {
        if ob.Margins[0]<4 || ob.Margins[1]<4 || ob.Margins[2]<4 {
            return ob,fmt.Errorf("FACE_FOREHEAD_OR_SIDE_CROPPED margins=%v",ob.Margins)
        }
    } else {
        for _,v:=range ob.Margins {
            if v<4{return ob,fmt.Errorf("SILHOUETTE_CROPPED margins=%v",ob.Margins)}
        }
    }
    ob.UpperBandWidth=bandWidth(mask,.14,.34,miny,maxy)
    ob.MiddleBandWidth=bandWidth(mask,.42,.62,miny,maxy)
    ob.LowerBandWidth=bandWidth(mask,.72,.92,miny,maxy)
    if ob.UpperBandWidth==0 || ob.MiddleBandWidth==0 || ob.LowerBandWidth==0 {
        return ob,errors.New("SILHOUETTE_MISSING_BANDS")
    }
    if meta.View=="face" {ob.Result="PASS_FACE_TOP_AND_SIDE_FRAMING_ONLY"} else {ob.Result="PASS_FULL_BODY_ALPHA_COMPLETENESS_ONLY"}
    return ob,nil
}
func Evaluate(indexPath string) (Report,error) {
    result:=Report{Schema:"scp.r009.shape_alpha_oracle.v1",
        CropScreen:"NOT_VERIFIED",AnatomicalAccuracyAccepted:false,
        SexFromImageInferred:false,GarmentClearanceAccepted:false,
        FaceIdentityAccepted:false}
    raw,err:=os.ReadFile(indexPath)
    if err!=nil{return result,err}
    var index Index
    if err=json.Unmarshal(raw,&index);err!=nil{return result,err}
    if index.Schema!="scp.r009.source_original_alpha_masks.v1" ||
        !validDigest(index.SourceSHA) || index.FileCount!=6 ||
        len(index.Images)!=6 || index.Pose!="REST" || index.Pixels!="RGBA_FILM_TRANSPARENT" ||
        index.FullBodyAccepted || index.FaceAccepted || index.CollisionAccepted {
        return result,errors.New("INDEX_OR_SCIENCE_CONTRACT_REJECT")
    }
    expected:=map[string]bool{
        "AsterOriginal/front":true,"AsterOriginal/side":true,"AsterOriginal/face":true,
        "JuniperOriginal/front":true,"JuniperOriginal/side":true,"JuniperOriginal/face":true}
    seen:=map[string]bool{}
    root:=filepath.Dir(indexPath)
    for _,image:=range index.Images {
        key:=image.Actor+"/"+image.View
        if !expected[key] || seen[key] || image.Preset!="adventure" ||
            image.VisualAccepted || !validDigest(image.SHA256) ||
            (math.IsNaN(image.CameraScale) || math.IsInf(image.CameraScale,0)) || image.CameraScale<=0 {
            return result,errors.New("INVALID_DUPLICATE_OR_UNTRUSTED_CAMERA_VIEW")
        }
        seen[key]=true
        o,err:=inspect(filepath.Join(root,image.Name),image)
        if err!=nil {return result,fmt.Errorf("%s: %w",key,err)}
        result.Captures=append(result.Captures,o)
    }
    sort.Slice(result.Captures,func(i,j int)bool{
        a,b:=result.Captures[i],result.Captures[j]
        return a.Actor+"/"+a.View<b.Actor+"/"+b.View
    })
    result.SourceSHA=index.SourceSHA
    result.Count=len(result.Captures)
    result.CropScreen="PASS_ALL_SIX_ALPHA_FRAMES_GEOMETRIC_ONLY"
    return result,nil
}
func main() {
    index:=flag.String("index","","Native Blender PNG index JSON")
    output:=flag.String("out","","Output JSON receipt")
    flag.Parse()
    if *index=="" || *output==""{fmt.Fprintln(os.Stderr,"-index and -out required");os.Exit(2)}
    r,err:=Evaluate(*index)
    if err!=nil{fmt.Fprintln(os.Stderr,"SHAPE_ALPHA_ORACLE_REJECT:",err);os.Exit(1)}
    out,err:=json.MarshalIndent(r,"","  ")
    if err!=nil {panic(err)}
    if err:=os.WriteFile(*output,append(out,'\n'),0644);err!=nil{panic(err)}
    fmt.Println(r.CropScreen,"observations",r.Count)
}
