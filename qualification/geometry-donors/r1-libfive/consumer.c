/* Original public-safe C API consumer; no donor source copied. */
#include <libfive.h>
#include <math.h>
#include <stdio.h>

static int near(float got, float want) {
  return isfinite(got) && fabsf(got - want) < 0.000001f;
}

int main(void) {
  libfive_tree axis = libfive_tree_x();
  libfive_tree constant = libfive_tree_const(3.5f);
  if (!axis || !constant) {
    fprintf(stderr, "LIBFIVE_C_API_CONSTRUCTOR_FAIL\n");
    return 2;
  }
  libfive_vec3 a = {1.25f, -2.0f, 0.5f};
  libfive_vec3 b = {-0.75f, 0.0f, 2.0f};
  float x1 = libfive_tree_eval_f(axis,a);
  float x2 = libfive_tree_eval_f(axis,b);
  float c = libfive_tree_eval_f(constant,a);
  int ok = near(x1,1.25f) && near(x2,-0.75f) && near(c,3.5f);
  libfive_tree_delete(axis);
  libfive_tree_delete(constant);
  if (!ok) {
    fprintf(stderr, "LIBFIVE_C_API_REFERENCE_FAIL x1=%g x2=%g c=%g\n",x1,x2,c);
    return 1;
  }
  printf("LIBFIVE_C_API_REFERENCE_PASS x1=%.6f x2=%.6f const=%.6f\n",x1,x2,c);
  return 0;
}
