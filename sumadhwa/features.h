// Mission 3 optimized feature pipeline. Interface matches the starter sketch.
// FFT is iterative radix-2 DIT with twiddles and bit-reversal indices prepared
// once by begin(), removing per-frame trigonometric calls.
#pragma once
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct FeatCfg {
  int fs = 16000, win = 480, hop = 320, nfft = 512, mels = 40, mfcc = 0;
};

class FeaturePipeline {
 public:
  FeatCfg c;
  bool ok = false;

  bool begin(const FeatCfg &cfg) {
    end();
    c = cfg;
    if (c.nfft < 16 || c.nfft > 2048 || (c.nfft & (c.nfft - 1)) ||
        c.win > c.nfft || c.win < 2 || c.hop < 1 || c.mels < 1 ||
        c.mels > 128 || c.mfcc < 0 || c.mfcc > c.mels || c.fs < 2) return false;
    nb = c.nfft / 2 + 1;
    window = alloc(c.win); re = alloc(c.nfft); im = alloc(c.nfft);
    pw = alloc(nb); melw = alloc((size_t)c.mels * nb); melv = alloc(c.mels);
    twr = alloc(c.nfft / 2); twi = alloc(c.nfft / 2);
    bitrev = (uint16_t *)malloc(sizeof(uint16_t) * c.nfft);
    if (c.mfcc) dct = alloc((size_t)c.mfcc * c.mels);
    if (!window || !re || !im || !pw || !melw || !melv || !twr || !twi ||
        !bitrev || (c.mfcc && !dct)) { end(); return false; }

    for (int n = 0; n < c.win; ++n)
      window[n] = 0.5f - 0.5f * cosf(2.0f * (float)M_PI * n / (c.win - 1));

    // FFT twiddles exp(-j*2*pi*k/nfft), reused at every stage.
    for (int k = 0; k < c.nfft / 2; ++k) {
      float a = 2.0f * (float)M_PI * k / c.nfft;
      twr[k] = cosf(a); twi[k] = -sinf(a);
    }
    int bits = 0;
    while ((1 << bits) < c.nfft) ++bits;
    for (int i = 0; i < c.nfft; ++i) {
      unsigned v = (unsigned)i, r = 0;
      for (int b = 0; b < bits; ++b) { r = (r << 1) | (v & 1u); v >>= 1; }
      bitrev[i] = (uint16_t)r;
    }

    auto hz2mel = [](double f) { return 2595.0 * log10(1.0 + f / 700.0); };
    auto mel2hz = [](double m) { return 700.0 * (pow(10.0, m / 2595.0) - 1.0); };
    double m0 = hz2mel(20.0), m1 = hz2mel(c.fs / 2.0);
    double *edge = (double *)malloc(sizeof(double) * (c.mels + 2));
    if (!edge) { end(); return false; }
    for (int i = 0; i < c.mels + 2; ++i)
      edge[i] = mel2hz(m0 + (m1 - m0) * i / (c.mels + 1));
    for (int m = 0; m < c.mels; ++m) {
      const double lo = edge[m], ce = edge[m + 1], hi = edge[m + 2];
      for (int k = 0; k < nb; ++k) {
        double f = (double)k * c.fs / c.nfft, w = 0;
        if (f > lo && f <= ce) w = (f - lo) / (ce - lo);
        else if (f > ce && f < hi) w = (hi - f) / (hi - ce);
        melw[(size_t)m * nb + k] = (float)w;
      }
    }
    free(edge);
    for (int q = 0; q < c.mfcc; ++q)
      for (int m = 0; m < c.mels; ++m)
        dct[(size_t)q * c.mels + m] = (float)((q == 0 ? sqrt(1.0 / c.mels) : sqrt(2.0 / c.mels)) *
          cos(M_PI * q * (2 * m + 1) / (2.0 * c.mels)));
    ok = true;
    return true;
  }

  int outSize() const { return c.mfcc ? c.mfcc : c.mels; }

  void compute(const float *frame, float *out) {
    for (int n = 0; n < c.win; ++n) { re[n] = frame[n] * window[n]; im[n] = 0; }
    for (int n = c.win; n < c.nfft; ++n) { re[n] = 0; im[n] = 0; }
    fft();
    for (int k = 0; k < nb; ++k)
      pw[k] = (re[k] * re[k] + im[k] * im[k]) / c.nfft;
    for (int m = 0; m < c.mels; ++m) {
      const float *w = melw + (size_t)m * nb;
      float sum = 0;
      for (int k = 0; k < nb; ++k) sum += w[k] * pw[k];
      melv[m] = 10.0f * log10f(sum > 1e-10f ? sum : 1e-10f);
    }
    if (!c.mfcc) { memcpy(out, melv, sizeof(float) * c.mels); return; }
    for (int q = 0; q < c.mfcc; ++q) {
      const float *d = dct + (size_t)q * c.mels;
      float sum = 0;
      for (int m = 0; m < c.mels; ++m) sum += d[m] * melv[m];
      out[q] = sum;
    }
  }

  void end() {
    free(window); free(re); free(im); free(pw); free(melw); free(melv);
    free(twr); free(twi); free(bitrev); free(dct);
    window = re = im = pw = melw = melv = twr = twi = dct = nullptr;
    bitrev = nullptr; nb = 0; ok = false;
  }
  ~FeaturePipeline() { end(); }

 private:
  int nb = 0;
  float *window = nullptr, *re = nullptr, *im = nullptr, *pw = nullptr;
  float *melw = nullptr, *melv = nullptr, *twr = nullptr, *twi = nullptr, *dct = nullptr;
  uint16_t *bitrev = nullptr;

  static float *alloc(size_t n) { return (float *)malloc(sizeof(float) * n); }

  void fft() {
    for (int i = 0; i < c.nfft; ++i) {
      int j = bitrev[i];
      if (j > i) {
        float t = re[i]; re[i] = re[j]; re[j] = t;
        t = im[i]; im[i] = im[j]; im[j] = t;
      }
    }
    for (int len = 2; len <= c.nfft; len <<= 1) {
      int half = len >> 1, stride = c.nfft / len;
      for (int base = 0; base < c.nfft; base += len) {
        for (int j = 0; j < half; ++j) {
          int a = base + j, b = a + half, ti = j * stride;
          float vr = re[b] * twr[ti] - im[b] * twi[ti];
          float vi = re[b] * twi[ti] + im[b] * twr[ti];
          float ur = re[a], ui = im[a];
          re[a] = ur + vr; im[a] = ui + vi;
          re[b] = ur - vr; im[b] = ui - vi;
        }
      }
    }
  }
};
