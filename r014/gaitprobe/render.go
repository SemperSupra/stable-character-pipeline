package main

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"math"
	"os"
	"path/filepath"
)

const W = 720
const H = 404

var background = color.RGBA{244, 245, 247, 255}
var ink = color.RGBA{55, 65, 81, 255}
var leftInk = color.RGBA{36, 117, 175, 255}
var rightInk = color.RGBA{176, 79, 49, 255}
var planted = color.RGBA{27, 132, 73, 255}
var airborne = color.RGBA{188, 133, 19, 255}

func pixel(im *image.RGBA, x, y int, c color.RGBA) {
	if x >= 0 && x < W && y >= 0 && y < H {
		im.SetRGBA(x, y, c)
	}
}
func line(im *image.RGBA, x0, y0, x1, y1 int, c color.RGBA) {
	dx := int(math.Abs(float64(x1 - x0)))
	dy := -int(math.Abs(float64(y1 - y0)))
	sx := -1
	if x0 < x1 {
		sx = 1
	}
	sy := -1
	if y0 < y1 {
		sy = 1
	}
	err := dx + dy
	for {
		pixel(im, x0, y0, c)
		pixel(im, x0+1, y0, c)
		if x0 == x1 && y0 == y1 {
			break
		}
		e := 2 * err
		if e >= dy {
			err += dy
			x0 += sx
		}
		if e <= dx {
			err += dx
			y0 += sy
		}
	}
}
func circle(im *image.RGBA, x, y, r int, c color.RGBA) {
	for yy := -r; yy <= r; yy++ {
		for xx := -r; xx <= r; xx++ {
			if xx*xx+yy*yy <= r*r {
				pixel(im, x+xx, y+yy, c)
			}
		}
	}
}
func project(v Vec3) (int, int) {
	return int(math.Round(62 + (v.X+.15)*125 + v.Y*27)), int(math.Round(336 - v.Z*275 + v.Y*65))
}
func Render(frames []Frame, dir string) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	for _, f := range frames {
		img := image.NewRGBA(image.Rect(0, 0, W, H))
		draw.Draw(img, img.Bounds(), &image.Uniform{background}, image.Point{}, draw.Src)
		line(img, 20, 336, W-25, 336, ink)
		for i := 0; i < 8; i++ {
			x := int(62 + float64(i)*100)
			line(img, x, 332, x, 340, color.RGBA{140, 145, 153, 255})
		}
		for _, pair := range []struct {
			leg LegFrame
			c   color.RGBA
		}{{f.Left, leftInk}, {f.Right, rightInk}} {
			l := pair.leg
			hx, hy := project(l.Hip)
			kx, ky := project(l.Knee)
			ax, ay := project(l.Ankle)
			line(img, hx, hy, kx, ky, pair.c)
			line(img, kx, ky, ax, ay, pair.c)
			circle(img, hx, hy, 5, ink)
			circle(img, kx, ky, 4, pair.c)
			c := airborne
			if l.Contact {
				c = planted
			}
			circle(img, ax, ay, 6, c)
		}
		lx, ly := project(f.Left.Hip)
		rx, ry := project(f.Right.Hip)
		line(img, lx, ly, rx, ry, ink)
		// The root marker visibly moves while stance-feet remain world-locked.
		cx, cy := project(Vec3{f.Root.X, f.Root.Y, HipHeight + .11})
		circle(img, cx, cy, 4, ink)
		file, err := os.Create(filepath.Join(dir, fmt.Sprintf("gait_%04d.png", f.Number-1)))
		if err != nil {
			return err
		}
		if err = png.Encode(file, img); err != nil {
			file.Close()
			return err
		}
		if err = file.Close(); err != nil {
			return err
		}
	}
	return nil
}
