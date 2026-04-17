var __getOwnPropNames = Object.getOwnPropertyNames;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};

// node_modules/grpc-web/index.js
var require_grpc_web = __commonJS({
  "node_modules/grpc-web/index.js"(exports2, module2) {
    var n;
    var p = p || {};
    var q = exports2 || self;
    function r(a2, b2) {
      a2 = a2.split(".");
      b2 = b2 || q;
      for (var c = 0; c < a2.length; c++) if (b2 = b2[a2[c]], b2 == null) return null;
      return b2;
    }
    function t(a2) {
      var b2 = typeof a2;
      return b2 == "object" && a2 != null || b2 == "function";
    }
    function aa(a2) {
      return Object.prototype.hasOwnProperty.call(a2, u) && a2[u] || (a2[u] = ++ba);
    }
    var u = "closure_uid_" + (Math.random() * 1e9 >>> 0);
    var ba = 0;
    function ca(a2, b2, c) {
      return a2.call.apply(a2.bind, arguments);
    }
    function da(a2, b2, c) {
      if (!a2) throw Error();
      if (arguments.length > 2) {
        var d = Array.prototype.slice.call(arguments, 2);
        return function() {
          var e = Array.prototype.slice.call(arguments);
          Array.prototype.unshift.apply(e, d);
          return a2.apply(b2, e);
        };
      }
      return function() {
        return a2.apply(b2, arguments);
      };
    }
    function w(a2, b2, c) {
      w = Function.prototype.bind && Function.prototype.bind.toString().indexOf("native code") != -1 ? ca : da;
      return w.apply(null, arguments);
    }
    function x(a2, b2) {
      function c() {
      }
      c.prototype = b2.prototype;
      a2.N = b2.prototype;
      a2.prototype = new c();
      a2.prototype.constructor = a2;
      a2.aa = function(d, e, g) {
        for (var f = Array(arguments.length - 2), h = 2; h < arguments.length; h++) f[h - 2] = arguments[h];
        return b2.prototype[e].apply(d, f);
      };
    }
    var ea = class {
      constructor(a2) {
        this.g = a2 || {};
      }
      get(a2) {
        return this.g[a2];
      }
    };
    var fa = class {
      constructor(a2, b2, c) {
        var d = new ea();
        this.j = a2;
        this.h = b2;
        this.g = c;
        this.i = d;
      }
      getRequestMessage() {
        return this.j;
      }
      getMethodDescriptor() {
        return this.h;
      }
      getMetadata() {
        return this.g;
      }
      getCallOptions() {
        return this.i;
      }
    };
    var ha = class {
      constructor(a2, b2, c = {}, d = null) {
        this.i = a2;
        this.g = c;
        this.h = b2;
        this.j = d;
      }
      getResponseMessage() {
        return this.i;
      }
      getMetadata() {
        return this.g;
      }
      getMethodDescriptor() {
        return this.h;
      }
      getStatus() {
        return this.j;
      }
    };
    function ia(a2, b2, c = {}) {
      return new fa(b2, a2, c);
    }
    function ja(a2, b2, c = {}, d = null) {
      return new ha(b2, a2, c, d);
    }
    var ka = class {
      constructor(a2, b2, c, d, e, g) {
        this.name = a2;
        this.g = e;
        this.h = g;
      }
      getName() {
        return this.name;
      }
    };
    ka.prototype.getName = ka.prototype.getName;
    var la = class {
      constructor(a2) {
        this.g = a2;
      }
      on(a2, b2) {
        return a2 == "data" || a2 == "error" ? this : this.g.on(a2, b2);
      }
      removeListener(a2, b2) {
        return this.g.removeListener(a2, b2);
      }
      cancel() {
        this.g.cancel();
      }
    };
    function ma(a2) {
      switch (a2) {
        case 0:
          return "No Error";
        case 1:
          return "Access denied to content document";
        case 2:
          return "File not found";
        case 3:
          return "Firefox silently errored";
        case 4:
          return "Application custom error";
        case 5:
          return "An exception occurred";
        case 6:
          return "Http response at 400 or 500 level";
        case 7:
          return "Request was aborted";
        case 8:
          return "Request timed out";
        case 9:
          return "The resource is not available offline";
        default:
          return "Unrecognized error code";
      }
    }
    function y(a2, b2) {
      if (Error.captureStackTrace) Error.captureStackTrace(this, y);
      else {
        const c = Error().stack;
        c && (this.stack = c);
      }
      a2 && (this.message = String(a2));
      b2 !== void 0 && (this.cause = b2);
    }
    x(y, Error);
    y.prototype.name = "CustomError";
    function na(a2, b2) {
      a2 = a2.split("%s");
      let c = "";
      const d = a2.length - 1;
      for (let e = 0; e < d; e++) c += a2[e] + (e < b2.length ? b2[e] : "%s");
      y.call(this, c + a2[d]);
    }
    x(na, y);
    na.prototype.name = "AssertionError";
    function oa(a2, b2) {
      throw new na("Failure" + (a2 ? ": " + a2 : ""), Array.prototype.slice.call(arguments, 1));
    }
    function pa(a2, b2) {
      function c(l) {
        l == qa ? f.o = l : l == B ? f.o = l : ra(f, h, k, "invalid frame byte");
        f.h = sa;
        f.g = 0;
        f.l = 0;
      }
      function d(l) {
        f.l++;
        f.g = (f.g << 8) + l;
        f.l == 4 && (f.h = ta, f.m = 0, typeof Uint8Array !== "undefined" ? f.i = new Uint8Array(f.g) : f.i = Array(f.g), f.g == 0 && g());
      }
      function e(l) {
        f.i[f.m++] = l;
        f.m == f.g && g();
      }
      function g() {
        var l = {};
        l[f.o] = f.i;
        f.j.push(l);
        f.h = ua;
      }
      var f = a2, h, k = 0;
      for (b2 instanceof Uint8Array || b2 instanceof Array ? h = b2 : h = new Uint8Array(b2); k < h.length; ) {
        switch (f.h) {
          case va:
            ra(f, h, k, "stream already broken");
            break;
          case ua:
            c(h[k]);
            break;
          case sa:
            d(h[k]);
            break;
          case ta:
            e(h[k]);
            break;
          default:
            throw Error("unexpected parser state: " + f.h);
        }
        f.v++;
        k++;
      }
      a2 = f.j;
      f.j = [];
      return a2.length > 0 ? a2 : null;
    }
    var wa = class {
      constructor() {
        this.u = null;
        this.j = [];
        this.v = 0;
        this.h = ua;
        this.l = this.g = this.o = 0;
        this.i = null;
        this.m = 0;
      }
    };
    var ua = 0;
    var sa = 1;
    var ta = 2;
    var va = 3;
    var qa = 0;
    var B = 128;
    function ra(a2, b2, c, d) {
      a2.h = va;
      a2.u = "The stream is broken @" + a2.v + "/" + c + ". Error: " + d + ". With input:\n" + b2;
      throw Error(a2.u);
    }
    function xa(a2) {
      switch (a2) {
        case 200:
          return 0;
        case 400:
          return 3;
        case 401:
          return 16;
        case 403:
          return 7;
        case 404:
          return 5;
        case 409:
          return 10;
        case 412:
          return 9;
        case 429:
          return 8;
        case 499:
          return 1;
        case 500:
          return 2;
        case 501:
          return 12;
        case 503:
          return 14;
        case 504:
          return 4;
        default:
          return 2;
      }
    }
    function ya(a2) {
      switch (a2) {
        case 0:
          return "OK";
        case 1:
          return "CANCELLED";
        case 2:
          return "UNKNOWN";
        case 3:
          return "INVALID_ARGUMENT";
        case 4:
          return "DEADLINE_EXCEEDED";
        case 5:
          return "NOT_FOUND";
        case 6:
          return "ALREADY_EXISTS";
        case 7:
          return "PERMISSION_DENIED";
        case 16:
          return "UNAUTHENTICATED";
        case 8:
          return "RESOURCE_EXHAUSTED";
        case 9:
          return "FAILED_PRECONDITION";
        case 10:
          return "ABORTED";
        case 11:
          return "OUT_OF_RANGE";
        case 12:
          return "UNIMPLEMENTED";
        case 13:
          return "INTERNAL";
        case 14:
          return "UNAVAILABLE";
        case 15:
          return "DATA_LOSS";
        default:
          return "";
      }
    }
    var C = class extends Error {
      constructor(a2, b2, c = {}) {
        super(b2);
        this.code = a2;
        this.metadata = c;
      }
      toString() {
        let a2 = `RpcError(${ya(this.code) || String(this.code)})`;
        this.message && (a2 += ": " + this.message);
        return a2;
      }
    };
    C.prototype.name = "RpcError";
    var za = Array.prototype.indexOf ? function(a2, b2) {
      return Array.prototype.indexOf.call(a2, b2, void 0);
    } : function(a2, b2) {
      if (typeof a2 === "string") return typeof b2 !== "string" || b2.length != 1 ? -1 : a2.indexOf(b2, 0);
      for (let c = 0; c < a2.length; c++) if (c in a2 && a2[c] === b2) return c;
      return -1;
    };
    function Aa() {
      var a2 = q.navigator;
      return a2 && (a2 = a2.userAgent) ? a2 : "";
    }
    function D(a2) {
      return Aa().indexOf(a2) != -1;
    }
    function Ba(a2) {
      Ba[" "](a2);
      return a2;
    }
    Ba[" "] = function() {
    };
    var Ca = D("Trident") || D("MSIE");
    var Da = D("Gecko") && !(Aa().toLowerCase().indexOf("webkit") != -1 && !D("Edge")) && !(D("Trident") || D("MSIE")) && !D("Edge");
    var Fa = class {
      constructor(a2) {
        if (Ea !== Ea) throw Error("SafeUrl is not meant to be built directly");
        this.g = a2;
      }
      toString() {
        return this.g.toString();
      }
    };
    var Ea = {};
    new Fa("about:invalid#zClosurez");
    new Fa("about:blank");
    var Ga = {};
    var Ha = class {
      constructor() {
        if (Ga !== Ga) throw Error("SafeStyle is not meant to be built directly");
      }
      toString() {
        return "".toString();
      }
    };
    new Ha();
    function Ia(a2, b2) {
      for (const c in a2) b2.call(void 0, a2[c], c, a2);
    }
    function Ja(a2, b2) {
      const c = {};
      for (const d in a2) c[d] = b2.call(void 0, a2[d], d, a2);
      return c;
    }
    var Ka = "constructor hasOwnProperty isPrototypeOf propertyIsEnumerable toLocaleString toString valueOf".split(" ");
    function La(a2, b2) {
      let c, d;
      for (let e = 1; e < arguments.length; e++) {
        d = arguments[e];
        for (c in d) a2[c] = d[c];
        for (let g = 0; g < Ka.length; g++) c = Ka[g], Object.prototype.hasOwnProperty.call(d, c) && (a2[c] = d[c]);
      }
    }
    var Ma = {};
    var Na = class {
      constructor() {
        if (Ma !== Ma) throw Error("SafeStyleSheet is not meant to be built directly");
      }
      toString() {
        return "".toString();
      }
    };
    new Na();
    var Oa = {};
    var Pa = class {
      constructor() {
        var a2 = q.trustedTypes && q.trustedTypes.emptyHTML || "";
        if (Oa !== Oa) throw Error("SafeHtml is not meant to be built directly");
        this.g = a2;
      }
      toString() {
        return this.g.toString();
      }
    };
    new Pa();
    function Qa(a2) {
      var b2 = 1;
      a2 = a2.split(":");
      const c = [];
      for (; b2 > 0 && a2.length; ) c.push(a2.shift()), b2--;
      a2.length && c.push(a2.join(":"));
      return c;
    }
    function E() {
      0 != Ra && (Sa[aa(this)] = this);
      this.v = this.v;
      this.o = this.o;
    }
    var Ra = 0;
    var Sa = {};
    E.prototype.v = false;
    E.prototype.dispose = function() {
      if (!this.v && (this.v = true, this.C(), 0 != Ra)) {
        var a2 = aa(this);
        if (0 != Ra && this.o && this.o.length > 0) throw Error(this + " did not empty its onDisposeCallbacks queue. This probably means it overrode dispose() or disposeInternal() without calling the superclass' method.");
        delete Sa[a2];
      }
    };
    E.prototype.C = function() {
      if (this.o) for (; this.o.length; ) this.o.shift()();
    };
    var Ta = Object.freeze || function(a2) {
      return a2;
    };
    function F(a2, b2) {
      this.type = a2;
      this.g = this.target = b2;
      this.defaultPrevented = false;
    }
    F.prototype.h = function() {
      this.defaultPrevented = true;
    };
    var Ua = (function() {
      if (!q.addEventListener || !Object.defineProperty) return false;
      var a2 = false, b2 = Object.defineProperty({}, "passive", { get: function() {
        a2 = true;
      } });
      try {
        const c = () => {
        };
        q.addEventListener("test", c, b2);
        q.removeEventListener("test", c, b2);
      } catch (c) {
      }
      return a2;
    })();
    function G(a2, b2) {
      F.call(this, a2 ? a2.type : "");
      this.relatedTarget = this.g = this.target = null;
      this.button = this.screenY = this.screenX = this.clientY = this.clientX = 0;
      this.key = "";
      this.metaKey = this.shiftKey = this.altKey = this.ctrlKey = false;
      this.state = null;
      this.pointerId = 0;
      this.pointerType = "";
      this.i = null;
      a2 && this.init(a2, b2);
    }
    x(G, F);
    var Va = Ta({ 2: "touch", 3: "pen", 4: "mouse" });
    G.prototype.init = function(a2, b2) {
      var c = this.type = a2.type, d = a2.changedTouches && a2.changedTouches.length ? a2.changedTouches[0] : null;
      this.target = a2.target || a2.srcElement;
      this.g = b2;
      if (b2 = a2.relatedTarget) {
        if (Da) {
          a: {
            try {
              Ba(b2.nodeName);
              var e = true;
              break a;
            } catch (g) {
            }
            e = false;
          }
          e || (b2 = null);
        }
      } else c == "mouseover" ? b2 = a2.fromElement : c == "mouseout" && (b2 = a2.toElement);
      this.relatedTarget = b2;
      d ? (this.clientX = d.clientX !== void 0 ? d.clientX : d.pageX, this.clientY = d.clientY !== void 0 ? d.clientY : d.pageY, this.screenX = d.screenX || 0, this.screenY = d.screenY || 0) : (this.clientX = a2.clientX !== void 0 ? a2.clientX : a2.pageX, this.clientY = a2.clientY !== void 0 ? a2.clientY : a2.pageY, this.screenX = a2.screenX || 0, this.screenY = a2.screenY || 0);
      this.button = a2.button;
      this.key = a2.key || "";
      this.ctrlKey = a2.ctrlKey;
      this.altKey = a2.altKey;
      this.shiftKey = a2.shiftKey;
      this.metaKey = a2.metaKey;
      this.pointerId = a2.pointerId || 0;
      this.pointerType = typeof a2.pointerType === "string" ? a2.pointerType : Va[a2.pointerType] || "";
      this.state = a2.state;
      this.i = a2;
      a2.defaultPrevented && G.N.h.call(this);
    };
    G.prototype.h = function() {
      G.N.h.call(this);
      var a2 = this.i;
      a2.preventDefault ? a2.preventDefault() : a2.returnValue = false;
    };
    var H = "closure_listenable_" + (Math.random() * 1e6 | 0);
    var Wa = 0;
    function Xa(a2, b2, c, d, e) {
      this.listener = a2;
      this.proxy = null;
      this.src = b2;
      this.type = c;
      this.capture = !!d;
      this.M = e;
      this.key = ++Wa;
      this.D = this.L = false;
    }
    function I(a2) {
      a2.D = true;
      a2.listener = null;
      a2.proxy = null;
      a2.src = null;
      a2.M = null;
    }
    function J(a2) {
      this.src = a2;
      this.g = {};
      this.h = 0;
    }
    J.prototype.add = function(a2, b2, c, d, e) {
      var g = a2.toString();
      a2 = this.g[g];
      a2 || (a2 = this.g[g] = [], this.h++);
      var f = Ya(a2, b2, d, e);
      f > -1 ? (b2 = a2[f], c || (b2.L = false)) : (b2 = new Xa(b2, this.src, g, !!d, e), b2.L = c, a2.push(b2));
      return b2;
    };
    function Za(a2, b2) {
      var c = b2.type;
      if (c in a2.g) {
        var d = a2.g[c], e = za(d, b2), g;
        (g = e >= 0) && Array.prototype.splice.call(d, e, 1);
        g && (I(b2), a2.g[c].length == 0 && (delete a2.g[c], a2.h--));
      }
    }
    function Ya(a2, b2, c, d) {
      for (var e = 0; e < a2.length; ++e) {
        var g = a2[e];
        if (!g.D && g.listener == b2 && g.capture == !!c && g.M == d) return e;
      }
      return -1;
    }
    var $a = "closure_lm_" + (Math.random() * 1e6 | 0);
    var ab = {};
    var bb = 0;
    function cb(a2, b2, c, d, e) {
      if (d && d.once) db(a2, b2, c, d, e);
      else if (Array.isArray(b2)) for (var g = 0; g < b2.length; g++) cb(a2, b2[g], c, d, e);
      else c = eb(c), a2 && a2[H] ? a2.j.add(String(b2), c, false, t(d) ? !!d.capture : !!d, e) : fb(a2, b2, c, false, d, e);
    }
    function fb(a2, b2, c, d, e, g) {
      if (!b2) throw Error("Invalid event type");
      var f = t(e) ? !!e.capture : !!e, h = gb(a2);
      h || (a2[$a] = h = new J(a2));
      c = h.add(b2, c, d, f, g);
      if (!c.proxy) {
        d = hb();
        c.proxy = d;
        d.src = a2;
        d.listener = c;
        if (a2.addEventListener) Ua || (e = f), e === void 0 && (e = false), a2.addEventListener(b2.toString(), d, e);
        else if (a2.attachEvent) a2.attachEvent(mb(b2.toString()), d);
        else if (a2.addListener && a2.removeListener) a2.addListener(d);
        else throw Error("addEventListener and attachEvent are unavailable.");
        bb++;
      }
    }
    function hb() {
      function a2(c) {
        return b2.call(a2.src, a2.listener, c);
      }
      const b2 = nb;
      return a2;
    }
    function db(a2, b2, c, d, e) {
      if (Array.isArray(b2)) for (var g = 0; g < b2.length; g++) db(a2, b2[g], c, d, e);
      else c = eb(c), a2 && a2[H] ? a2.j.add(String(b2), c, true, t(d) ? !!d.capture : !!d, e) : fb(a2, b2, c, true, d, e);
    }
    function ob(a2, b2, c, d, e) {
      if (Array.isArray(b2)) for (var g = 0; g < b2.length; g++) ob(a2, b2[g], c, d, e);
      else (d = t(d) ? !!d.capture : !!d, c = eb(c), a2 && a2[H]) ? (a2 = a2.j, b2 = String(b2).toString(), b2 in a2.g && (g = a2.g[b2], c = Ya(g, c, d, e), c > -1 && (I(g[c]), Array.prototype.splice.call(g, c, 1), g.length == 0 && (delete a2.g[b2], a2.h--)))) : a2 && (a2 = gb(a2)) && (b2 = a2.g[b2.toString()], a2 = -1, b2 && (a2 = Ya(b2, c, d, e)), (c = a2 > -1 ? b2[a2] : null) && pb(c));
    }
    function pb(a2) {
      if (typeof a2 !== "number" && a2 && !a2.D) {
        var b2 = a2.src;
        if (b2 && b2[H]) Za(b2.j, a2);
        else {
          var c = a2.type, d = a2.proxy;
          b2.removeEventListener ? b2.removeEventListener(c, d, a2.capture) : b2.detachEvent ? b2.detachEvent(mb(c), d) : b2.addListener && b2.removeListener && b2.removeListener(d);
          bb--;
          (c = gb(b2)) ? (Za(c, a2), c.h == 0 && (c.src = null, b2[$a] = null)) : I(a2);
        }
      }
    }
    function mb(a2) {
      return a2 in ab ? ab[a2] : ab[a2] = "on" + a2;
    }
    function nb(a2, b2) {
      if (a2.D) a2 = true;
      else {
        b2 = new G(b2, this);
        var c = a2.listener, d = a2.M || a2.src;
        a2.L && pb(a2);
        a2 = c.call(d, b2);
      }
      return a2;
    }
    function gb(a2) {
      a2 = a2[$a];
      return a2 instanceof J ? a2 : null;
    }
    var qb = "__closure_events_fn_" + (Math.random() * 1e9 >>> 0);
    function eb(a2) {
      if (typeof a2 === "function") return a2;
      a2[qb] || (a2[qb] = function(b2) {
        return a2.handleEvent(b2);
      });
      return a2[qb];
    }
    function K() {
      E.call(this);
      this.j = new J(this);
      this.W = this;
      this.S = null;
    }
    x(K, E);
    K.prototype[H] = true;
    K.prototype.removeEventListener = function(a2, b2, c, d) {
      ob(this, a2, b2, c, d);
    };
    function L(a2, b2) {
      var c, d = a2.S;
      if (d) for (c = []; d; d = d.S) c.push(d);
      a2 = a2.W;
      d = b2.type || b2;
      if (typeof b2 === "string") b2 = new F(b2, a2);
      else if (b2 instanceof F) b2.target = b2.target || a2;
      else {
        var e = b2;
        b2 = new F(d, a2);
        La(b2, e);
      }
      e = true;
      if (c) for (var g = c.length - 1; g >= 0; g--) {
        var f = b2.g = c[g];
        e = M(f, d, true, b2) && e;
      }
      f = b2.g = a2;
      e = M(f, d, true, b2) && e;
      e = M(f, d, false, b2) && e;
      if (c) for (g = 0; g < c.length; g++) f = b2.g = c[g], e = M(f, d, false, b2) && e;
    }
    K.prototype.C = function() {
      K.N.C.call(this);
      if (this.j) {
        var a2 = this.j, b2 = 0, c;
        for (c in a2.g) {
          for (var d = a2.g[c], e = 0; e < d.length; e++) ++b2, I(d[e]);
          delete a2.g[c];
          a2.h--;
        }
      }
      this.S = null;
    };
    function M(a2, b2, c, d) {
      b2 = a2.j.g[String(b2)];
      if (!b2) return true;
      b2 = b2.concat();
      for (var e = true, g = 0; g < b2.length; ++g) {
        var f = b2[g];
        if (f && !f.D && f.capture == c) {
          var h = f.listener, k = f.M || f.src;
          f.L && Za(a2.j, f);
          e = h.call(k, d) !== false && e;
        }
      }
      return e && !d.defaultPrevented;
    }
    var rb = q;
    function sb(a2, b2, c) {
      if (typeof a2 === "function") c && (a2 = w(a2, c));
      else if (a2 && typeof a2.handleEvent == "function") a2 = w(a2.handleEvent, a2);
      else throw Error("Invalid listener argument");
      return Number(b2) > 2147483647 ? -1 : rb.setTimeout(a2, b2 || 0);
    }
    var N = class {
      constructor(a2, b2) {
        this.name = a2;
        this.value = b2;
      }
      toString() {
        return this.name;
      }
    };
    var O = new N("OFF", Infinity);
    var tb = new N("SEVERE", 1e3);
    var ub = new N("CONFIG", 700);
    var vb = new N("FINE", 500);
    var wb = class {
    };
    var xb;
    var yb = class {
      constructor(a2, b2, c) {
        this.reset(a2 || O, b2, c, void 0, void 0);
      }
      reset() {
      }
    };
    function zb(a2) {
      if (a2.g) return a2.g;
      if (a2.h) return zb(a2.h);
      oa("Root logger has no level set.");
      return O;
    }
    function Ab(a2, b2) {
      for (; a2; ) a2.j.forEach((c) => {
        c(b2);
      }), a2 = a2.h;
    }
    var Bb = class {
      constructor(a2, b2 = null) {
        this.g = null;
        this.j = [];
        this.h = b2 || null;
        this.i = [];
        this.l = { getName: () => a2 };
      }
    };
    function P(a2, b2) {
      var c = a2.entries[b2];
      if (c) return c;
      c = P(a2, b2.slice(0, Math.max(b2.lastIndexOf("."), 0)));
      const d = new Bb(b2, c);
      a2.entries[b2] = d;
      c.i.push(d);
      return d;
    }
    var Cb = class {
      constructor() {
        this.entries = {};
        const a2 = new Bb("");
        a2.g = ub;
        this.entries[""] = a2;
      }
    };
    var Db;
    function Eb() {
      Db || (Db = new Cb());
      return Db;
    }
    function Fb(a2, b2, c) {
      var d;
      if (d = a2) {
        if (d = a2 && b2) {
          d = b2.value;
          var e = a2 ? zb(P(Eb(), a2.getName())) : O;
          d = d >= e.value;
        }
      }
      d && (b2 = b2 || O, d = P(Eb(), a2.getName()), typeof c === "function" && (c = c()), xb || (xb = new wb()), a2 = a2.getName(), a2 = new yb(b2, c, a2), Ab(d, a2));
    }
    function Gb(a2, b2) {
      a2 && Fb(a2, tb, b2);
    }
    function Q(a2, b2) {
      a2 && Fb(a2, vb, b2);
    }
    function Hb() {
    }
    Hb.prototype.g = null;
    function Ib(a2) {
      var b2;
      (b2 = a2.g) || (b2 = {}, Jb(a2) && (b2[0] = true, b2[1] = true), b2 = a2.g = b2);
      return b2;
    }
    var Kb;
    function Lb() {
    }
    x(Lb, Hb);
    function Mb(a2) {
      return (a2 = Jb(a2)) ? new ActiveXObject(a2) : new XMLHttpRequest();
    }
    function Jb(a2) {
      if (!a2.h && typeof XMLHttpRequest == "undefined" && typeof ActiveXObject != "undefined") {
        const b2 = ["MSXML2.XMLHTTP.6.0", "MSXML2.XMLHTTP.3.0", "MSXML2.XMLHTTP", "Microsoft.XMLHTTP"];
        for (let c = 0; c < b2.length; c++) {
          const d = b2[c];
          try {
            return new ActiveXObject(d), a2.h = d;
          } catch (e) {
          }
        }
        throw Error("Could not create ActiveXObject. ActiveX might be disabled, or MSXML might not be installed");
      }
      return a2.h;
    }
    Kb = new Lb();
    var Nb = RegExp("^(?:([^:/?#.]+):)?(?://(?:([^\\\\/?#]*)@)?([^\\\\/?#]*?)(?::([0-9]+))?(?=[\\\\/?#]|$))?([^?#]+)?(?:\\?([^#]*))?(?:#([\\s\\S]*))?$");
    function R(a2) {
      K.call(this);
      this.headers = /* @__PURE__ */ new Map();
      this.K = a2 || null;
      this.i = false;
      this.J = this.g = null;
      this.T = this.G = "";
      this.m = 0;
      this.A = "";
      this.l = this.R = this.F = this.P = false;
      this.u = 0;
      this.H = null;
      this.B = Ob;
      this.I = this.O = false;
    }
    x(R, K);
    var Ob = "";
    R.prototype.h = P(Eb(), "goog.net.XhrIo").l;
    var Pb = /^https?$/i;
    var Qb = ["POST", "PUT"];
    function Rb(a2, b2, c) {
      if (a2.g) throw Error("[goog.net.XhrIo] Object is active with another request=" + a2.G + "; newUri=" + b2);
      a2.G = b2;
      a2.A = "";
      a2.m = 0;
      a2.T = "POST";
      a2.P = false;
      a2.i = true;
      a2.g = a2.K ? Mb(a2.K) : Mb(Kb);
      a2.J = a2.K ? Ib(a2.K) : Ib(Kb);
      a2.g.onreadystatechange = w(a2.U, a2);
      try {
        Q(a2.h, S(a2, "Opening Xhr")), a2.R = true, a2.g.open("POST", String(b2), true), a2.R = false;
      } catch (g) {
        Q(a2.h, S(a2, "Error opening Xhr: " + g.message));
        Sb(a2, g);
        return;
      }
      b2 = c || "";
      c = new Map(a2.headers);
      const d = Array.from(c.keys()).find((g) => "content-type" == g.toLowerCase()), e = q.FormData && b2 instanceof q.FormData;
      !(za(Qb, "POST") >= 0) || d || e || c.set("Content-Type", "application/x-www-form-urlencoded;charset=utf-8");
      for (const [g, f] of c) a2.g.setRequestHeader(g, f);
      a2.B && (a2.g.responseType = a2.B);
      "withCredentials" in a2.g && a2.g.withCredentials !== a2.O && (a2.g.withCredentials = a2.O);
      try {
        Tb(a2), a2.u > 0 && (a2.I = Ub(a2.g), Q(a2.h, S(a2, "Will abort after " + a2.u + "ms if incomplete, xhr2 " + a2.I)), a2.I ? (a2.g.timeout = a2.u, a2.g.ontimeout = w(a2.V, a2)) : a2.H = sb(a2.V, a2.u, a2)), Q(a2.h, S(a2, "Sending request")), a2.F = true, a2.g.send(b2), a2.F = false;
      } catch (g) {
        Q(a2.h, S(a2, "Send error: " + g.message)), Sb(a2, g);
      }
    }
    function Ub(a2) {
      return Ca && typeof a2.timeout === "number" && a2.ontimeout !== void 0;
    }
    n = R.prototype;
    n.V = function() {
      typeof p != "undefined" && this.g && (this.A = "Timed out after " + this.u + "ms, aborting", this.m = 8, Q(this.h, S(this, this.A)), L(this, "timeout"), this.abort(8));
    };
    function Sb(a2, b2) {
      a2.i = false;
      a2.g && (a2.l = true, a2.g.abort(), a2.l = false);
      a2.A = b2;
      a2.m = 5;
      Vb(a2);
      T(a2);
    }
    function Vb(a2) {
      a2.P || (a2.P = true, L(a2, "complete"), L(a2, "error"));
    }
    n.abort = function(a2) {
      this.g && this.i && (Q(this.h, S(this, "Aborting")), this.i = false, this.l = true, this.g.abort(), this.l = false, this.m = a2 || 7, L(this, "complete"), L(this, "abort"), T(this));
    };
    n.C = function() {
      this.g && (this.i && (this.i = false, this.l = true, this.g.abort(), this.l = false), T(this, true));
      R.N.C.call(this);
    };
    n.U = function() {
      this.v || (this.R || this.F || this.l ? Wb(this) : this.X());
    };
    n.X = function() {
      Wb(this);
    };
    function Wb(a2) {
      if (a2.i && typeof p != "undefined") {
        if (a2.J[1] && U(a2) == 4 && a2.getStatus() == 2) Q(a2.h, S(a2, "Local request error detected and ignored"));
        else if (a2.F && U(a2) == 4) sb(a2.U, 0, a2);
        else if (L(a2, "readystatechange"), U(a2) == 4) {
          Q(a2.h, S(a2, "Request complete"));
          a2.i = false;
          try {
            const f = a2.getStatus();
            a: switch (f) {
              case 200:
              case 201:
              case 202:
              case 204:
              case 206:
              case 304:
              case 1223:
                var b2 = true;
                break a;
              default:
                b2 = false;
            }
            var c;
            if (!(c = b2)) {
              var d;
              if (d = f === 0) {
                var e = String(a2.G).match(Nb)[1] || null;
                !e && q.self && q.self.location && (e = q.self.location.protocol.slice(
                  0,
                  -1
                ));
                d = !Pb.test(e ? e.toLowerCase() : "");
              }
              c = d;
            }
            if (c) L(a2, "complete"), L(a2, "success");
            else {
              a2.m = 6;
              try {
                var g = U(a2) > 2 ? a2.g.statusText : "";
              } catch (h) {
                Q(a2.h, "Can not get status: " + h.message), g = "";
              }
              a2.A = g + " [" + a2.getStatus() + "]";
              Vb(a2);
            }
          } finally {
            T(a2);
          }
        }
      }
    }
    function T(a2, b2) {
      if (a2.g) {
        Tb(a2);
        const c = a2.g, d = a2.J[0] ? () => {
        } : null;
        a2.g = null;
        a2.J = null;
        b2 || L(a2, "ready");
        try {
          c.onreadystatechange = d;
        } catch (e) {
          Gb(a2.h, "Problem encountered resetting onreadystatechange: " + e.message);
        }
      }
    }
    function Tb(a2) {
      a2.g && a2.I && (a2.g.ontimeout = null);
      a2.H && (rb.clearTimeout(a2.H), a2.H = null);
    }
    n.isActive = function() {
      return !!this.g;
    };
    function U(a2) {
      return a2.g ? a2.g.readyState : 0;
    }
    n.getStatus = function() {
      try {
        return U(this) > 2 ? this.g.status : -1;
      } catch (a2) {
        return -1;
      }
    };
    function Xb(a2) {
      try {
        if (!a2.g) return null;
        if ("response" in a2.g) return a2.g.response;
        switch (a2.B) {
          case Ob:
          case "text":
            return a2.g.responseText;
          case "arraybuffer":
            if ("mozResponseArrayBuffer" in a2.g) return a2.g.mozResponseArrayBuffer;
        }
        Gb(a2.h, "Response type " + a2.B + " is not supported on this browser");
        return null;
      } catch (b2) {
        return Q(a2.h, "Can not get response: " + b2.message), null;
      }
    }
    function Yb(a2) {
      const b2 = {};
      a2 = (a2.g && U(a2) >= 2 ? a2.g.getAllResponseHeaders() || "" : "").split("\r\n");
      for (let d = 0; d < a2.length; d++) {
        if (/^[\s\xa0]*$/.test(a2[d])) continue;
        var c = Qa(a2[d]);
        const e = c[0];
        c = c[1];
        if (typeof c !== "string") continue;
        c = c.trim();
        const g = b2[e] || [];
        b2[e] = g;
        g.push(c);
      }
      return Ja(b2, function(d) {
        return d.join(", ");
      });
    }
    function S(a2, b2) {
      return b2 + " [" + a2.T + " " + a2.G + " " + a2.getStatus() + "]";
    }
    var Zb = {};
    var V = null;
    function $b(a2) {
      var b2 = a2.length, c = b2 * 3 / 4;
      c % 3 ? c = Math.floor(c) : "=.".indexOf(a2[b2 - 1]) != -1 && (c = "=.".indexOf(a2[b2 - 2]) != -1 ? c - 2 : c - 1);
      var d = new Uint8Array(c), e = 0;
      ac(a2, function(g) {
        d[e++] = g;
      });
      return e !== c ? d.subarray(0, e) : d;
    }
    function ac(a2, b2) {
      function c(k) {
        for (; d < a2.length; ) {
          var l = a2.charAt(d++), m = V[l];
          if (m != null) return m;
          if (!/^[\s\xa0]*$/.test(l)) throw Error("Unknown base64 encoding at char: " + l);
        }
        return k;
      }
      bc();
      for (var d = 0; ; ) {
        var e = c(-1), g = c(0), f = c(64), h = c(64);
        if (h === 64 && e === -1) break;
        b2(e << 2 | g >> 4);
        f != 64 && (b2(g << 4 & 240 | f >> 2), h != 64 && b2(f << 6 & 192 | h));
      }
    }
    function bc() {
      if (!V) {
        V = {};
        for (var a2 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789".split(""), b2 = ["+/=", "+/", "-_=", "-_.", "-_"], c = 0; c < 5; c++) {
          var d = a2.concat(b2[c].split(""));
          Zb[c] = d;
          for (var e = 0; e < d.length; e++) {
            var g = d[e];
            V[g] === void 0 && (V[g] = e);
          }
        }
      }
    }
    var cc = ["content-type", "grpc-status", "grpc-message"];
    function W(a2, b2) {
      if (b2.code != 0) {
        var c = new C(b2.code, decodeURIComponent(b2.message || ""), b2.metadata);
        for (let d = 0; d < a2.j.length; d++) a2.j[d](c);
      }
      b2 = { code: b2.code, details: decodeURIComponent(b2.message || ""), metadata: b2.metadata };
      for (c = 0; c < a2.m.length; c++) a2.m[c](b2);
    }
    function dc(a2, b2) {
      for (let c = 0; c < a2.l.length; c++) a2.l[c](b2);
    }
    function ec(a2) {
      for (let b2 = 0; b2 < a2.i.length; b2++) a2.i[b2]();
    }
    function X(a2, b2) {
      b2 = a2.indexOf(b2);
      b2 > -1 && a2.splice(b2, 1);
    }
    var Y = class {
      constructor(a2) {
        this.g = a2.$;
        this.v = null;
        this.h = [];
        this.m = [];
        this.l = [];
        this.j = [];
        this.i = [];
        this.u = false;
        this.o = 0;
        this.A = new wa();
        const b2 = this;
        cb(this.g, "readystatechange", function() {
          var c = b2.g;
          if (c = c.g ? c.g.getResponseHeader("Content-Type") : null) {
            c = c.toLowerCase();
            if (c.lastIndexOf("application/grpc-web-text", 0) == 0) {
              c = b2.g;
              try {
                var d = c.g ? c.g.responseText : "";
              } catch (h) {
                Q(c.h, "Can not get responseText: " + h.message), d = "";
              }
              c = d || "";
              d = c.length - c.length % 4;
              c = c.substr(b2.o, d - b2.o);
              if (c.length == 0) return;
              b2.o = d;
              c = $b(c);
            } else if (c.lastIndexOf(
              "application/grpc",
              0
            ) == 0) c = new Uint8Array(Xb(b2.g));
            else {
              W(b2, new C(2, "Unknown Content-type received."));
              return;
            }
            d = null;
            try {
              d = pa(b2.A, c);
            } catch (h) {
              W(b2, new C(2, "Error in parsing response body"));
            }
            if (d) for (c = 0; c < d.length; c++) {
              if (qa in d[c]) {
                var e = d[c][qa];
                if (e) {
                  var g = false;
                  let h;
                  try {
                    h = b2.v(e), g = true;
                  } catch (k) {
                    W(b2, new C(13, `Error when deserializing response data; error: ${k}, response: ${h}`));
                  }
                  if (g) {
                    e = b2;
                    g = h;
                    for (var f = 0; f < e.h.length; f++) e.h[f](g);
                  }
                }
              }
              if (B in d[c] && d[c][B].length > 0) {
                e = "";
                for (g = 0; g < d[c][B].length; g++) e += String.fromCharCode(d[c][B][g]);
                e = e.trim().split("\r\n");
                g = {};
                for (f = 0; f < e.length; f++) {
                  const h = e[f].indexOf(":");
                  g[e[f].substring(0, h).trim()] = e[f].substring(h + 1).trim();
                }
                e = g;
                g = 0;
                f = "";
                "grpc-status" in e && (g = Number(e["grpc-status"]), delete e["grpc-status"]);
                "grpc-message" in e && (f = e["grpc-message"], delete e["grpc-message"]);
                W(b2, new C(g, f, e));
              }
            }
          }
        });
        cb(this.g, "complete", function() {
          var c = b2.g.m, d = 2, e = "";
          const g = {};
          d = Yb(b2.g);
          const f = {};
          for (var h in d) d.hasOwnProperty(h) && (f[h.toLowerCase()] = d[h]);
          Object.keys(f).forEach((k) => {
            cc.includes(k) || (g[k] = f[k]);
          });
          dc(b2, g);
          h = -1;
          if (c != 0) {
            switch (c) {
              case 7:
                d = 10;
                break;
              case 8:
                d = 4;
                break;
              case 6:
                h = b2.g.getStatus();
                d = xa(h);
                break;
              default:
                d = 14;
            }
            d == 10 && b2.u || (e = ma(c), h != -1 && (e += ", http status code: " + h), W(b2, new C(d, e)));
          } else c = false, "grpc-status" in f && (d = Number(f["grpc-status"]), "grpc-message" in f && (e = f["grpc-message"]), d != 0 && (W(b2, new C(d, e || "", f)), c = true)), c || ec(b2);
        });
      }
      on(a2, b2) {
        a2 == "data" ? this.h.push(b2) : a2 == "status" ? this.m.push(b2) : a2 == "metadata" ? this.l.push(b2) : a2 == "end" ? this.i.push(b2) : a2 == "error" && this.j.push(b2);
        return this;
      }
      removeListener(a2, b2) {
        a2 == "data" ? X(this.h, b2) : a2 == "status" ? X(this.m, b2) : a2 == "metadata" ? X(this.l, b2) : a2 == "end" ? X(this.i, b2) : a2 == "error" && X(this.j, b2);
        return this;
      }
      cancel() {
        this.u = true;
        this.g.abort();
      }
    };
    Y.prototype.cancel = Y.prototype.cancel;
    Y.prototype.removeListener = Y.prototype.removeListener;
    Y.prototype.on = Y.prototype.on;
    function fc(a2) {
      let b2 = "";
      Ia(a2, function(c, d) {
        b2 += d;
        b2 += ":";
        b2 += c;
        b2 += "\r\n";
      });
      return b2;
    }
    function hc(a2, b2) {
      return b2.reduce((c, d) => (e) => d.intercept(e, c), a2);
    }
    function ic(a2, b2, c) {
      let d = false, e = null, g = false;
      a2.on("data", function(f) {
        d = true;
        e = f;
      });
      a2.on("error", function(f) {
        f.code == 0 || g || (g = true, b2(f, null));
      });
      a2.on("status", function(f) {
        f.code == 0 || g ? c && b2(null, null, f) : (g = true, b2({ code: f.code, message: f.details, metadata: f.metadata }, null));
      });
      if (c) a2.on("metadata", function(f) {
        b2(null, null, null, f);
      });
      a2.on("end", function() {
        g || (d ? c ? b2(null, e, null, null, true) : b2(null, e) : b2({ code: 2, message: "Incomplete response" }));
        c && b2(null, null);
      });
    }
    function jc(a2, b2, c) {
      var d = b2.getMethodDescriptor(), e = c + d.getName();
      c = a2.i ? a2.i : new R();
      c.O = a2.j;
      const g = new Y({ $: c });
      g.v = d.h;
      var f = b2.getMetadata();
      for (var h in f) c.headers.set(h, f[h]);
      a2.g == "text" ? (c.headers.set("Content-Type", "application/grpc-web-text"), c.headers.set("Accept", "application/grpc-web-text")) : c.headers.set("Content-Type", "application/grpc-web+proto");
      c.headers.set("X-User-Agent", "grpc-web-javascript/0.1");
      c.headers.set("X-Grpc-Web", "1");
      c.headers.has("deadline") && (h = Number(c.headers.get("deadline")), h = Math.ceil(h - (/* @__PURE__ */ new Date()).getTime()), c.headers.delete("deadline"), h === Infinity && (h = 0), h > 0 && (c.headers.set("grpc-timeout", h + "m"), c.u = Math.max(0, Math.max(1e3, Math.ceil(h * 1.1)))));
      if (a2.l) {
        h = c.headers;
        f = {};
        for (k of h.keys()) f[k] = h.get(k);
        var k = f;
        c.headers.clear();
        b: {
          for (l in k) {
            var l = false;
            break b;
          }
          l = true;
        }
        if (!l) if (k = fc(k), typeof e === "string") {
          if (l = encodeURIComponent("$httpHeaders"), k = k != null ? "=" + encodeURIComponent(String(k)) : "", l += k) k = e.indexOf("#"), k < 0 && (k = e.length), h = e.indexOf("?"), h < 0 || h > k ? (h = k, f = "") : f = e.substring(h + 1, k), e = [e.slice(0, h), f, e.slice(k)], k = e[1], e[1] = l ? k ? k + "&" + l : l : k, e = e[0] + (e[1] ? "?" + e[1] : "") + e[2];
        } else e.g("$httpHeaders", k);
      }
      b2 = (0, d.g)(b2.getRequestMessage());
      d = b2.length;
      l = [0, 0, 0, 0];
      k = new Uint8Array(5 + d);
      for (h = 3; h >= 0; h--) l[h] = d % 256, d >>>= 8;
      k.set(new Uint8Array(l), 1);
      k.set(b2, 5);
      b2 = k;
      if (a2.g == "text") {
        a2 = b2;
        var m;
        m === void 0 && (m = 0);
        bc();
        m = Zb[m];
        b2 = Array(Math.floor(a2.length / 3));
        d = m[64] || "";
        for (l = k = 0; k < a2.length - 2; k += 3) {
          var z = a2[k], A = a2[k + 1];
          f = a2[k + 2];
          h = m[z >> 2];
          z = m[(z & 3) << 4 | A >> 4];
          A = m[(A & 15) << 2 | f >> 6];
          f = m[f & 63];
          b2[l++] = h + z + A + f;
        }
        h = 0;
        f = d;
        switch (a2.length - k) {
          case 2:
            h = a2[k + 1], f = m[(h & 15) << 2] || d;
          case 1:
            a2 = a2[k], b2[l] = m[a2 >> 2] + m[(a2 & 3) << 4 | h >> 4] + f + d;
        }
        b2 = b2.join("");
      } else a2.g == "binary" && (c.B = "arraybuffer");
      Rb(c, e, b2);
      return g;
    }
    function kc(a2, b2, c, d, e, g = {}) {
      const f = b2.substr(0, b2.length - e.name.length), h = g && g.signal;
      return hc((k) => new Promise((l, m) => {
        if (h && h.aborted) {
          const v = new C(1, "Aborted");
          v.cause = h.reason;
          m(v);
        } else {
          var z = jc(a2, k, f), A, ib, jb;
          ic(z, (v, lc, kb, lb, mc) => {
            v ? m(v) : mc ? jb = lc : kb ? ib = kb : lb ? A = lb : l(ja(k.getMethodDescriptor(), jb, A, ib));
          }, true);
          h && h.addEventListener("abort", () => {
            z.cancel();
            const v = new C(1, "Aborted");
            v.cause = h.reason;
            m(v);
          });
        }
      }), a2.m).call(a2, ia(e, c, d)).then((k) => k.getResponseMessage());
    }
    var Z = class {
      constructor(a2 = {}, b2) {
        this.g = a2.format || r("format", a2) || "text";
        this.l = a2.ca || r("suppressCorsPreflight", a2) || false;
        this.j = a2.withCredentials || r("withCredentials", a2) || false;
        this.h = a2.ba || r("streamInterceptors", a2) || [];
        this.m = a2.da || r("unaryInterceptors", a2) || [];
        this.i = b2 || null;
      }
      Y(a2, b2, c, d, e) {
        const g = a2.substr(0, a2.length - d.name.length);
        a2 = hc((f) => jc(this, f, g), this.h).call(this, ia(d, b2, c));
        ic(a2, e, false);
        return new la(a2);
      }
      unaryCall(a2, b2, c, d, e = {}) {
        return kc(this, a2, b2, c, d, e);
      }
      Z(a2, b2, c, d) {
        const e = a2.substr(0, a2.length - d.name.length);
        return hc((g) => jc(this, g, e), this.h).call(this, ia(d, b2, c));
      }
    };
    Z.prototype.serverStreaming = Z.prototype.Z;
    Z.prototype.unaryCall = Z.prototype.unaryCall;
    Z.prototype.rpcCall = Z.prototype.Y;
    module2.exports.CallOptions = ea;
    module2.exports.MethodDescriptor = ka;
    module2.exports.GrpcWebClientBase = Z;
    module2.exports.RpcError = C;
    module2.exports.StatusCode = { OK: 0, CANCELLED: 1, UNKNOWN: 2, INVALID_ARGUMENT: 3, DEADLINE_EXCEEDED: 4, NOT_FOUND: 5, ALREADY_EXISTS: 6, PERMISSION_DENIED: 7, UNAUTHENTICATED: 16, RESOURCE_EXHAUSTED: 8, FAILED_PRECONDITION: 9, ABORTED: 10, OUT_OF_RANGE: 11, UNIMPLEMENTED: 12, INTERNAL: 13, UNAVAILABLE: 14, DATA_LOSS: 15 };
    module2.exports.MethodType = { UNARY: "unary", SERVER_STREAMING: "server_streaming", BIDI_STREAMING: "bidi_streaming" };
    rb = typeof globalThis !== "undefined" && globalThis || self;
  }
});

// node_modules/google-protobuf/google-protobuf.js
var require_google_protobuf = __commonJS({
  "node_modules/google-protobuf/google-protobuf.js"(exports, module) {
    var COMPILED = true;
    var goog = goog || {};
    goog.global = exports || self;
    goog.exportPath_ = function(a2, b2, c, d) {
      a2 = a2.split(".");
      d = d || goog.global;
      a2[0] in d || "undefined" == typeof d.execScript || d.execScript("var " + a2[0]);
      for (var e; a2.length && (e = a2.shift()); ) if (a2.length || void 0 === b2) d = d[e] && d[e] !== Object.prototype[e] ? d[e] : d[e] = {};
      else if (!c && goog.isObject(b2) && goog.isObject(d[e])) for (var f in b2) b2.hasOwnProperty(f) && (d[e][f] = b2[f]);
      else d[e] = b2;
    };
    goog.define = function(a2, b2) {
      if (!COMPILED) {
        var c = goog.global.CLOSURE_UNCOMPILED_DEFINES, d = goog.global.CLOSURE_DEFINES;
        c && void 0 === c.nodeType && Object.prototype.hasOwnProperty.call(c, a2) ? b2 = c[a2] : d && void 0 === d.nodeType && Object.prototype.hasOwnProperty.call(d, a2) && (b2 = d[a2]);
      }
      return b2;
    };
    goog.FEATURESET_YEAR = 2012;
    goog.DEBUG = true;
    goog.LOCALE = "en";
    goog.TRUSTED_SITE = true;
    goog.DISALLOW_TEST_ONLY_CODE = COMPILED && !goog.DEBUG;
    goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING = false;
    goog.provide = function(a2) {
      if (goog.isInModuleLoader_()) throw Error("goog.provide cannot be used within a module.");
      if (!COMPILED && goog.isProvided_(a2)) throw Error('Namespace "' + a2 + '" already declared.');
      goog.constructNamespace_(a2);
    };
    goog.constructNamespace_ = function(a2, b2, c) {
      if (!COMPILED) {
        delete goog.implicitNamespaces_[a2];
        for (var d = a2; (d = d.substring(0, d.lastIndexOf("."))) && !goog.getObjectByName(d); ) goog.implicitNamespaces_[d] = true;
      }
      goog.exportPath_(a2, b2, c);
    };
    goog.NONCE_PATTERN_ = /^[\w+/_-]+[=]{0,2}$/;
    goog.getScriptNonce_ = function(a2) {
      a2 = (a2 || goog.global).document;
      return (a2 = a2.querySelector && a2.querySelector("script[nonce]")) && (a2 = a2.nonce || a2.getAttribute("nonce")) && goog.NONCE_PATTERN_.test(a2) ? a2 : "";
    };
    goog.VALID_MODULE_RE_ = /^[a-zA-Z_$][a-zA-Z0-9._$]*$/;
    goog.module = function(a2) {
      if ("string" !== typeof a2 || !a2 || -1 == a2.search(goog.VALID_MODULE_RE_)) throw Error("Invalid module identifier");
      if (!goog.isInGoogModuleLoader_()) throw Error("Module " + a2 + " has been loaded incorrectly. Note, modules cannot be loaded as normal scripts. They require some kind of pre-processing step. You're likely trying to load a module via a script tag or as a part of a concatenated bundle without rewriting the module. For more info see: https://github.com/google/closure-library/wiki/goog.module:-an-ES6-module-like-alternative-to-goog.provide.");
      if (goog.moduleLoaderState_.moduleName) throw Error("goog.module may only be called once per module.");
      goog.moduleLoaderState_.moduleName = a2;
      if (!COMPILED) {
        if (goog.isProvided_(a2)) throw Error('Namespace "' + a2 + '" already declared.');
        delete goog.implicitNamespaces_[a2];
      }
    };
    goog.module.get = function(a2) {
      return goog.module.getInternal_(a2);
    };
    goog.module.getInternal_ = function(a2) {
      if (!COMPILED) {
        if (a2 in goog.loadedModules_) return goog.loadedModules_[a2].exports;
        if (!goog.implicitNamespaces_[a2]) return a2 = goog.getObjectByName(a2), null != a2 ? a2 : null;
      }
      return null;
    };
    goog.ModuleType = { ES6: "es6", GOOG: "goog" };
    goog.moduleLoaderState_ = null;
    goog.isInModuleLoader_ = function() {
      return goog.isInGoogModuleLoader_() || goog.isInEs6ModuleLoader_();
    };
    goog.isInGoogModuleLoader_ = function() {
      return !!goog.moduleLoaderState_ && goog.moduleLoaderState_.type == goog.ModuleType.GOOG;
    };
    goog.isInEs6ModuleLoader_ = function() {
      if (goog.moduleLoaderState_ && goog.moduleLoaderState_.type == goog.ModuleType.ES6) return true;
      var a2 = goog.global.$jscomp;
      return a2 ? "function" != typeof a2.getCurrentModulePath ? false : !!a2.getCurrentModulePath() : false;
    };
    goog.module.declareLegacyNamespace = function() {
      if (!COMPILED && !goog.isInGoogModuleLoader_()) throw Error("goog.module.declareLegacyNamespace must be called from within a goog.module");
      if (!COMPILED && !goog.moduleLoaderState_.moduleName) throw Error("goog.module must be called prior to goog.module.declareLegacyNamespace.");
      goog.moduleLoaderState_.declareLegacyNamespace = true;
    };
    goog.declareModuleId = function(a2) {
      if (!COMPILED) {
        if (!goog.isInEs6ModuleLoader_()) throw Error("goog.declareModuleId may only be called from within an ES6 module");
        if (goog.moduleLoaderState_ && goog.moduleLoaderState_.moduleName) throw Error("goog.declareModuleId may only be called once per module.");
        if (a2 in goog.loadedModules_) throw Error('Module with namespace "' + a2 + '" already exists.');
      }
      if (goog.moduleLoaderState_) goog.moduleLoaderState_.moduleName = a2;
      else {
        var b2 = goog.global.$jscomp;
        if (!b2 || "function" != typeof b2.getCurrentModulePath) throw Error('Module with namespace "' + a2 + '" has been loaded incorrectly.');
        b2 = b2.require(b2.getCurrentModulePath());
        goog.loadedModules_[a2] = { exports: b2, type: goog.ModuleType.ES6, moduleId: a2 };
      }
    };
    goog.setTestOnly = function(a2) {
      if (goog.DISALLOW_TEST_ONLY_CODE) throw a2 = a2 || "", Error("Importing test-only code into non-debug environment" + (a2 ? ": " + a2 : "."));
    };
    goog.forwardDeclare = function(a2) {
    };
    COMPILED || (goog.isProvided_ = function(a2) {
      return a2 in goog.loadedModules_ || !goog.implicitNamespaces_[a2] && null != goog.getObjectByName(a2);
    }, goog.implicitNamespaces_ = { "goog.module": true });
    goog.getObjectByName = function(a2, b2) {
      a2 = a2.split(".");
      b2 = b2 || goog.global;
      for (var c = 0; c < a2.length; c++) if (b2 = b2[a2[c]], null == b2) return null;
      return b2;
    };
    goog.addDependency = function(a2, b2, c, d) {
      !COMPILED && goog.DEPENDENCIES_ENABLED && goog.debugLoader_.addDependency(a2, b2, c, d);
    };
    goog.ENABLE_DEBUG_LOADER = false;
    goog.logToConsole_ = function(a2) {
      goog.global.console && goog.global.console.error(a2);
    };
    goog.require = function(a2) {
      if (!COMPILED) {
        goog.ENABLE_DEBUG_LOADER && goog.debugLoader_.requested(a2);
        if (goog.isProvided_(a2)) {
          if (goog.isInModuleLoader_()) return goog.module.getInternal_(a2);
        } else if (goog.ENABLE_DEBUG_LOADER) {
          var b2 = goog.moduleLoaderState_;
          goog.moduleLoaderState_ = null;
          try {
            goog.debugLoader_.load_(a2);
          } finally {
            goog.moduleLoaderState_ = b2;
          }
        }
        return null;
      }
    };
    goog.requireType = function(a2) {
      return {};
    };
    goog.basePath = "";
    goog.abstractMethod = function() {
      throw Error("unimplemented abstract method");
    };
    goog.addSingletonGetter = function(a2) {
      a2.instance_ = void 0;
      a2.getInstance = function() {
        if (a2.instance_) return a2.instance_;
        goog.DEBUG && (goog.instantiatedSingletons_[goog.instantiatedSingletons_.length] = a2);
        return a2.instance_ = new a2();
      };
    };
    goog.instantiatedSingletons_ = [];
    goog.LOAD_MODULE_USING_EVAL = true;
    goog.SEAL_MODULE_EXPORTS = goog.DEBUG;
    goog.loadedModules_ = {};
    goog.DEPENDENCIES_ENABLED = !COMPILED && goog.ENABLE_DEBUG_LOADER;
    goog.TRANSPILE = "detect";
    goog.ASSUME_ES_MODULES_TRANSPILED = false;
    goog.TRUSTED_TYPES_POLICY_NAME = "goog";
    goog.hasBadLetScoping = null;
    goog.loadModule = function(a2) {
      var b2 = goog.moduleLoaderState_;
      try {
        goog.moduleLoaderState_ = { moduleName: "", declareLegacyNamespace: false, type: goog.ModuleType.GOOG };
        var c = {}, d = c;
        if ("function" === typeof a2) d = a2.call(void 0, d);
        else if ("string" === typeof a2) d = goog.loadModuleFromSource_.call(void 0, d, a2);
        else throw Error("Invalid module definition");
        var e = goog.moduleLoaderState_.moduleName;
        if ("string" === typeof e && e) goog.moduleLoaderState_.declareLegacyNamespace ? goog.constructNamespace_(e, d, c !== d) : goog.SEAL_MODULE_EXPORTS && Object.seal && "object" == typeof d && null != d && Object.seal(d), goog.loadedModules_[e] = { exports: d, type: goog.ModuleType.GOOG, moduleId: goog.moduleLoaderState_.moduleName };
        else throw Error('Invalid module name "' + e + '"');
      } finally {
        goog.moduleLoaderState_ = b2;
      }
    };
    goog.loadModuleFromSource_ = function(a, b) {
      eval(goog.CLOSURE_EVAL_PREFILTER_.createScript(b));
      return a;
    };
    goog.normalizePath_ = function(a2) {
      a2 = a2.split("/");
      for (var b2 = 0; b2 < a2.length; ) "." == a2[b2] ? a2.splice(b2, 1) : b2 && ".." == a2[b2] && a2[b2 - 1] && ".." != a2[b2 - 1] ? a2.splice(--b2, 2) : b2++;
      return a2.join("/");
    };
    goog.loadFileSync_ = function(a2) {
      if (goog.global.CLOSURE_LOAD_FILE_SYNC) return goog.global.CLOSURE_LOAD_FILE_SYNC(a2);
      try {
        var b2 = new goog.global.XMLHttpRequest();
        b2.open("get", a2, false);
        b2.send();
        return 0 == b2.status || 200 == b2.status ? b2.responseText : null;
      } catch (c) {
        return null;
      }
    };
    goog.typeOf = function(a2) {
      var b2 = typeof a2;
      return "object" != b2 ? b2 : a2 ? Array.isArray(a2) ? "array" : b2 : "null";
    };
    goog.isArrayLike = function(a2) {
      var b2 = goog.typeOf(a2);
      return "array" == b2 || "object" == b2 && "number" == typeof a2.length;
    };
    goog.isDateLike = function(a2) {
      return goog.isObject(a2) && "function" == typeof a2.getFullYear;
    };
    goog.isObject = function(a2) {
      var b2 = typeof a2;
      return "object" == b2 && null != a2 || "function" == b2;
    };
    goog.getUid = function(a2) {
      return Object.prototype.hasOwnProperty.call(a2, goog.UID_PROPERTY_) && a2[goog.UID_PROPERTY_] || (a2[goog.UID_PROPERTY_] = ++goog.uidCounter_);
    };
    goog.hasUid = function(a2) {
      return !!a2[goog.UID_PROPERTY_];
    };
    goog.removeUid = function(a2) {
      null !== a2 && "removeAttribute" in a2 && a2.removeAttribute(goog.UID_PROPERTY_);
      try {
        delete a2[goog.UID_PROPERTY_];
      } catch (b2) {
      }
    };
    goog.UID_PROPERTY_ = "closure_uid_" + (1e9 * Math.random() >>> 0);
    goog.uidCounter_ = 0;
    goog.cloneObject = function(a2) {
      var b2 = goog.typeOf(a2);
      if ("object" == b2 || "array" == b2) {
        if ("function" === typeof a2.clone) return a2.clone();
        if ("undefined" !== typeof Map && a2 instanceof Map) return new Map(a2);
        if ("undefined" !== typeof Set && a2 instanceof Set) return new Set(a2);
        b2 = "array" == b2 ? [] : {};
        for (var c in a2) b2[c] = goog.cloneObject(a2[c]);
        return b2;
      }
      return a2;
    };
    goog.bindNative_ = function(a2, b2, c) {
      return a2.call.apply(a2.bind, arguments);
    };
    goog.bindJs_ = function(a2, b2, c) {
      if (!a2) throw Error();
      if (2 < arguments.length) {
        var d = Array.prototype.slice.call(arguments, 2);
        return function() {
          var e = Array.prototype.slice.call(arguments);
          Array.prototype.unshift.apply(e, d);
          return a2.apply(b2, e);
        };
      }
      return function() {
        return a2.apply(b2, arguments);
      };
    };
    goog.bind = function(a2, b2, c) {
      Function.prototype.bind && -1 != Function.prototype.bind.toString().indexOf("native code") ? goog.bind = goog.bindNative_ : goog.bind = goog.bindJs_;
      return goog.bind.apply(null, arguments);
    };
    goog.partial = function(a2, b2) {
      var c = Array.prototype.slice.call(arguments, 1);
      return function() {
        var d = c.slice();
        d.push.apply(d, arguments);
        return a2.apply(this, d);
      };
    };
    goog.now = function() {
      return Date.now();
    };
    goog.globalEval = function(a2) {
      (0, eval)(a2);
    };
    goog.getCssName = function(a2, b2) {
      if ("." == String(a2).charAt(0)) throw Error('className passed in goog.getCssName must not start with ".". You passed: ' + a2);
      var c = function(e) {
        return goog.cssNameMapping_[e] || e;
      }, d = function(e) {
        e = e.split("-");
        for (var f = [], g = 0; g < e.length; g++) f.push(c(e[g]));
        return f.join("-");
      };
      d = goog.cssNameMapping_ ? "BY_WHOLE" == goog.cssNameMappingStyle_ ? c : d : function(e) {
        return e;
      };
      a2 = b2 ? a2 + "-" + d(b2) : d(a2);
      return goog.global.CLOSURE_CSS_NAME_MAP_FN ? goog.global.CLOSURE_CSS_NAME_MAP_FN(a2) : a2;
    };
    goog.setCssNameMapping = function(a2, b2) {
      goog.cssNameMapping_ = a2;
      goog.cssNameMappingStyle_ = b2;
    };
    !COMPILED && goog.global.CLOSURE_CSS_NAME_MAPPING && (goog.cssNameMapping_ = goog.global.CLOSURE_CSS_NAME_MAPPING);
    goog.GetMsgOptions = function() {
    };
    goog.getMsg = function(a2, b2, c) {
      c && c.html && (a2 = a2.replace(/</g, "&lt;"));
      c && c.unescapeHtmlEntities && (a2 = a2.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&"));
      b2 && (a2 = a2.replace(/\{\$([^}]+)}/g, function(d, e) {
        return null != b2 && e in b2 ? b2[e] : d;
      }));
      return a2;
    };
    goog.getMsgWithFallback = function(a2, b2) {
      return a2;
    };
    goog.exportSymbol = function(a2, b2, c) {
      goog.exportPath_(a2, b2, true, c);
    };
    goog.exportProperty = function(a2, b2, c) {
      a2[b2] = c;
    };
    goog.inherits = function(a2, b2) {
      function c() {
      }
      c.prototype = b2.prototype;
      a2.superClass_ = b2.prototype;
      a2.prototype = new c();
      a2.prototype.constructor = a2;
      a2.base = function(d, e, f) {
        for (var g = Array(arguments.length - 2), h = 2; h < arguments.length; h++) g[h - 2] = arguments[h];
        return b2.prototype[e].apply(d, g);
      };
    };
    goog.scope = function(a2) {
      if (goog.isInModuleLoader_()) throw Error("goog.scope is not supported within a module.");
      a2.call(goog.global);
    };
    COMPILED || (goog.global.COMPILED = COMPILED);
    goog.defineClass = function(a2, b2) {
      var c = b2.constructor, d = b2.statics;
      c && c != Object.prototype.constructor || (c = function() {
        throw Error("cannot instantiate an interface (no constructor defined).");
      });
      c = goog.defineClass.createSealingConstructor_(c, a2);
      a2 && goog.inherits(c, a2);
      delete b2.constructor;
      delete b2.statics;
      goog.defineClass.applyProperties_(c.prototype, b2);
      null != d && (d instanceof Function ? d(c) : goog.defineClass.applyProperties_(c, d));
      return c;
    };
    goog.defineClass.SEAL_CLASS_INSTANCES = goog.DEBUG;
    goog.defineClass.createSealingConstructor_ = function(a2, b2) {
      return goog.defineClass.SEAL_CLASS_INSTANCES ? function() {
        var c = a2.apply(this, arguments) || this;
        c[goog.UID_PROPERTY_] = c[goog.UID_PROPERTY_];
        return c;
      } : a2;
    };
    goog.defineClass.OBJECT_PROTOTYPE_FIELDS_ = "constructor hasOwnProperty isPrototypeOf propertyIsEnumerable toLocaleString toString valueOf".split(" ");
    goog.defineClass.applyProperties_ = function(a2, b2) {
      for (var c in b2) Object.prototype.hasOwnProperty.call(b2, c) && (a2[c] = b2[c]);
      for (var d = 0; d < goog.defineClass.OBJECT_PROTOTYPE_FIELDS_.length; d++) c = goog.defineClass.OBJECT_PROTOTYPE_FIELDS_[d], Object.prototype.hasOwnProperty.call(b2, c) && (a2[c] = b2[c]);
    };
    goog.identity_ = function(a2) {
      return a2;
    };
    goog.createTrustedTypesPolicy = function(a2) {
      var b2 = null, c = goog.global.trustedTypes;
      if (!c || !c.createPolicy) return b2;
      try {
        b2 = c.createPolicy(a2, { createHTML: goog.identity_, createScript: goog.identity_, createScriptURL: goog.identity_ });
      } catch (d) {
        goog.logToConsole_(d.message);
      }
      return b2;
    };
    !COMPILED && goog.DEPENDENCIES_ENABLED && (goog.isEdge_ = function() {
      return !!(goog.global.navigator && goog.global.navigator.userAgent ? goog.global.navigator.userAgent : "").match(/Edge\/(\d+)(\.\d)*/i);
    }, goog.inHtmlDocument_ = function() {
      var a2 = goog.global.document;
      return null != a2 && "write" in a2;
    }, goog.isDocumentLoading_ = function() {
      var a2 = goog.global.document;
      return a2.attachEvent ? "complete" != a2.readyState : "loading" == a2.readyState;
    }, goog.findBasePath_ = function() {
      if (void 0 != goog.global.CLOSURE_BASE_PATH && "string" === typeof goog.global.CLOSURE_BASE_PATH) goog.basePath = goog.global.CLOSURE_BASE_PATH;
      else if (goog.inHtmlDocument_()) {
        var a2 = goog.global.document, b2 = a2.currentScript;
        a2 = b2 ? [b2] : a2.getElementsByTagName("SCRIPT");
        for (b2 = a2.length - 1; 0 <= b2; --b2) {
          var c = a2[b2].src, d = c.lastIndexOf("?");
          d = -1 == d ? c.length : d;
          if ("base.js" == c.slice(d - 7, d)) {
            goog.basePath = c.slice(0, d - 7);
            break;
          }
        }
      }
    }, goog.findBasePath_(), goog.protectScriptTag_ = function(a2) {
      return a2.replace(/<\/(SCRIPT)/ig, "\\x3c/$1");
    }, goog.DebugLoader_ = function() {
      this.dependencies_ = {};
      this.idToPath_ = {};
      this.written_ = {};
      this.loadingDeps_ = [];
      this.depsToLoad_ = [];
      this.paused_ = false;
      this.factory_ = new goog.DependencyFactory();
      this.deferredCallbacks_ = {};
      this.deferredQueue_ = [];
    }, goog.DebugLoader_.prototype.bootstrap = function(a2, b2) {
      function c() {
        d && (goog.global.setTimeout(d, 0), d = null);
      }
      var d = b2;
      if (a2.length) {
        b2 = [];
        for (var e = 0; e < a2.length; e++) {
          var f = this.getPathFromDeps_(a2[e]);
          if (!f) throw Error("Unregonized namespace: " + a2[e]);
          b2.push(this.dependencies_[f]);
        }
        f = goog.require;
        var g = 0;
        for (e = 0; e < a2.length; e++) f(a2[e]), b2[e].onLoad(function() {
          ++g == a2.length && c();
        });
      } else c();
    }, goog.DebugLoader_.prototype.loadClosureDeps = function() {
      this.depsToLoad_.push(this.factory_.createDependency(goog.normalizePath_(goog.basePath + "deps.js"), "deps.js", [], [], {}));
      this.loadDeps_();
    }, goog.DebugLoader_.prototype.requested = function(a2, b2) {
      (a2 = this.getPathFromDeps_(a2)) && (b2 || this.areDepsLoaded_(this.dependencies_[a2].requires)) && (b2 = this.deferredCallbacks_[a2]) && (delete this.deferredCallbacks_[a2], b2());
    }, goog.DebugLoader_.prototype.setDependencyFactory = function(a2) {
      this.factory_ = a2;
    }, goog.DebugLoader_.prototype.load_ = function(a2) {
      if (this.getPathFromDeps_(a2)) {
        var b2 = this, c = [], d = function(e) {
          var f = b2.getPathFromDeps_(e);
          if (!f) throw Error("Bad dependency path or symbol: " + e);
          if (!b2.written_[f]) {
            b2.written_[f] = true;
            e = b2.dependencies_[f];
            for (f = 0; f < e.requires.length; f++) goog.isProvided_(e.requires[f]) || d(e.requires[f]);
            c.push(e);
          }
        };
        d(a2);
        a2 = !!this.depsToLoad_.length;
        this.depsToLoad_ = this.depsToLoad_.concat(c);
        this.paused_ || a2 || this.loadDeps_();
      } else goog.logToConsole_("goog.require could not find: " + a2);
    }, goog.DebugLoader_.prototype.loadDeps_ = function() {
      for (var a2 = this, b2 = this.paused_; this.depsToLoad_.length && !b2; ) (function() {
        var c = false, d = a2.depsToLoad_.shift(), e = false;
        a2.loading_(d);
        var f = { pause: function() {
          if (c) throw Error("Cannot call pause after the call to load.");
          b2 = true;
        }, resume: function() {
          c ? a2.resume_() : b2 = false;
        }, loaded: function() {
          if (e) throw Error("Double call to loaded.");
          e = true;
          a2.loaded_(d);
        }, pending: function() {
          for (var g = [], h = 0; h < a2.loadingDeps_.length; h++) g.push(a2.loadingDeps_[h]);
          return g;
        }, setModuleState: function(g) {
          goog.moduleLoaderState_ = {
            type: g,
            moduleName: "",
            declareLegacyNamespace: false
          };
        }, registerEs6ModuleExports: function(g, h, l) {
          l && (goog.loadedModules_[l] = { exports: h, type: goog.ModuleType.ES6, moduleId: l || "" });
        }, registerGoogModuleExports: function(g, h) {
          goog.loadedModules_[g] = { exports: h, type: goog.ModuleType.GOOG, moduleId: g };
        }, clearModuleState: function() {
          goog.moduleLoaderState_ = null;
        }, defer: function(g) {
          if (c) throw Error("Cannot register with defer after the call to load.");
          a2.defer_(d, g);
        }, areDepsLoaded: function() {
          return a2.areDepsLoaded_(d.requires);
        } };
        try {
          d.load(f);
        } finally {
          c = true;
        }
      })();
      b2 && this.pause_();
    }, goog.DebugLoader_.prototype.pause_ = function() {
      this.paused_ = true;
    }, goog.DebugLoader_.prototype.resume_ = function() {
      this.paused_ && (this.paused_ = false, this.loadDeps_());
    }, goog.DebugLoader_.prototype.loading_ = function(a2) {
      this.loadingDeps_.push(a2);
    }, goog.DebugLoader_.prototype.loaded_ = function(a2) {
      for (var b2 = 0; b2 < this.loadingDeps_.length; b2++) if (this.loadingDeps_[b2] == a2) {
        this.loadingDeps_.splice(b2, 1);
        break;
      }
      for (b2 = 0; b2 < this.deferredQueue_.length; b2++) if (this.deferredQueue_[b2] == a2.path) {
        this.deferredQueue_.splice(b2, 1);
        break;
      }
      if (this.loadingDeps_.length == this.deferredQueue_.length && !this.depsToLoad_.length) for (; this.deferredQueue_.length; ) this.requested(this.deferredQueue_.shift(), true);
      a2.loaded();
    }, goog.DebugLoader_.prototype.areDepsLoaded_ = function(a2) {
      for (var b2 = 0; b2 < a2.length; b2++) {
        var c = this.getPathFromDeps_(a2[b2]);
        if (!c || !(c in this.deferredCallbacks_ || goog.isProvided_(a2[b2]))) return false;
      }
      return true;
    }, goog.DebugLoader_.prototype.getPathFromDeps_ = function(a2) {
      return a2 in this.idToPath_ ? this.idToPath_[a2] : a2 in this.dependencies_ ? a2 : null;
    }, goog.DebugLoader_.prototype.defer_ = function(a2, b2) {
      this.deferredCallbacks_[a2.path] = b2;
      this.deferredQueue_.push(a2.path);
    }, goog.LoadController = function() {
    }, goog.LoadController.prototype.pause = function() {
    }, goog.LoadController.prototype.resume = function() {
    }, goog.LoadController.prototype.loaded = function() {
    }, goog.LoadController.prototype.pending = function() {
    }, goog.LoadController.prototype.registerEs6ModuleExports = function(a2, b2, c) {
    }, goog.LoadController.prototype.setModuleState = function(a2) {
    }, goog.LoadController.prototype.clearModuleState = function() {
    }, goog.LoadController.prototype.defer = function(a2) {
    }, goog.LoadController.prototype.areDepsLoaded = function() {
    }, goog.Dependency = function(a2, b2, c, d, e) {
      this.path = a2;
      this.relativePath = b2;
      this.provides = c;
      this.requires = d;
      this.loadFlags = e;
      this.loaded_ = false;
      this.loadCallbacks_ = [];
    }, goog.Dependency.prototype.getPathName = function() {
      var a2 = this.path, b2 = a2.indexOf("://");
      0 <= b2 && (a2 = a2.substring(b2 + 3), b2 = a2.indexOf("/"), 0 <= b2 && (a2 = a2.substring(b2 + 1)));
      return a2;
    }, goog.Dependency.prototype.onLoad = function(a2) {
      this.loaded_ ? a2() : this.loadCallbacks_.push(a2);
    }, goog.Dependency.prototype.loaded = function() {
      this.loaded_ = true;
      var a2 = this.loadCallbacks_;
      this.loadCallbacks_ = [];
      for (var b2 = 0; b2 < a2.length; b2++) a2[b2]();
    }, goog.Dependency.defer_ = false, goog.Dependency.callbackMap_ = {}, goog.Dependency.registerCallback_ = function(a2) {
      var b2 = Math.random().toString(32);
      goog.Dependency.callbackMap_[b2] = a2;
      return b2;
    }, goog.Dependency.unregisterCallback_ = function(a2) {
      delete goog.Dependency.callbackMap_[a2];
    }, goog.Dependency.callback_ = function(a2, b2) {
      if (a2 in goog.Dependency.callbackMap_) {
        for (var c = goog.Dependency.callbackMap_[a2], d = [], e = 1; e < arguments.length; e++) d.push(arguments[e]);
        c.apply(void 0, d);
      } else throw Error("Callback key " + a2 + " does not exist (was base.js loaded more than once?).");
    }, goog.Dependency.prototype.load = function(a2) {
      if (goog.global.CLOSURE_IMPORT_SCRIPT) goog.global.CLOSURE_IMPORT_SCRIPT(this.path) ? a2.loaded() : a2.pause();
      else if (goog.inHtmlDocument_()) {
        var b2 = goog.global.document;
        if ("complete" == b2.readyState && !goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING) {
          if (/\bdeps.js$/.test(this.path)) {
            a2.loaded();
            return;
          }
          throw Error('Cannot write "' + this.path + '" after document load');
        }
        var c = goog.getScriptNonce_();
        if (!goog.ENABLE_CHROME_APP_SAFE_SCRIPT_LOADING && goog.isDocumentLoading_()) {
          var d = function(h) {
            h.readyState && "complete" != h.readyState ? h.onload = d : (goog.Dependency.unregisterCallback_(e), a2.loaded());
          };
          var e = goog.Dependency.registerCallback_(d);
          c = c ? ' nonce="' + c + '"' : "";
          var f = '<script src="' + this.path + '"' + c + (goog.Dependency.defer_ ? " defer" : "") + ' id="script-' + e + '"><\/script>';
          f += "<script" + c + ">";
          f = goog.Dependency.defer_ ? f + ("document.getElementById('script-" + e + "').onload = function() {\n  goog.Dependency.callback_('" + e + "', this);\n};\n") : f + ("goog.Dependency.callback_('" + e + "', document.getElementById('script-" + e + "'));");
          f += "<\/script>";
          b2.write(goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createHTML(f) : f);
        } else {
          var g = b2.createElement("script");
          g.defer = goog.Dependency.defer_;
          g.async = false;
          c && (g.nonce = c);
          g.onload = function() {
            g.onload = null;
            a2.loaded();
          };
          g.src = goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createScriptURL(this.path) : this.path;
          b2.head.appendChild(g);
        }
      } else goog.logToConsole_("Cannot use default debug loader outside of HTML documents."), "deps.js" == this.relativePath ? (goog.logToConsole_("Consider setting CLOSURE_IMPORT_SCRIPT before loading base.js, or setting CLOSURE_NO_DEPS to true."), a2.loaded()) : a2.pause();
    }, goog.Es6ModuleDependency = function(a2, b2, c, d, e) {
      goog.Dependency.call(
        this,
        a2,
        b2,
        c,
        d,
        e
      );
    }, goog.inherits(goog.Es6ModuleDependency, goog.Dependency), goog.Es6ModuleDependency.prototype.load = function(a2) {
      function b2(k, n) {
        var m = "", p = goog.getScriptNonce_();
        p && (m = ' nonce="' + p + '"');
        k = n ? '<script type="module" crossorigin' + m + ">" + n + "<\/script>" : '<script type="module" crossorigin src="' + k + '"' + m + "><\/script>";
        d.write(goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createHTML(k) : k);
      }
      function c(k, n) {
        var m = d.createElement("script");
        m.defer = true;
        m.async = false;
        m.type = "module";
        m.setAttribute(
          "crossorigin",
          true
        );
        var p = goog.getScriptNonce_();
        p && (m.nonce = p);
        n ? m.text = goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createScript(n) : n : m.src = goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createScriptURL(k) : k;
        d.head.appendChild(m);
      }
      if (goog.global.CLOSURE_IMPORT_SCRIPT) goog.global.CLOSURE_IMPORT_SCRIPT(this.path) ? a2.loaded() : a2.pause();
      else if (goog.inHtmlDocument_()) {
        var d = goog.global.document, e = this;
        if (goog.isDocumentLoading_()) {
          var f = b2;
          goog.Dependency.defer_ = true;
        } else f = c;
        var g = goog.Dependency.registerCallback_(function() {
          goog.Dependency.unregisterCallback_(g);
          a2.setModuleState(goog.ModuleType.ES6);
        });
        f(void 0, 'goog.Dependency.callback_("' + g + '")');
        f(this.path, void 0);
        var h = goog.Dependency.registerCallback_(function(k) {
          goog.Dependency.unregisterCallback_(h);
          a2.registerEs6ModuleExports(e.path, k, goog.moduleLoaderState_.moduleName);
        });
        f(void 0, 'import * as m from "' + this.path + '"; goog.Dependency.callback_("' + h + '", m)');
        var l = goog.Dependency.registerCallback_(function() {
          goog.Dependency.unregisterCallback_(l);
          a2.clearModuleState();
          a2.loaded();
        });
        f(void 0, 'goog.Dependency.callback_("' + l + '")');
      } else goog.logToConsole_("Cannot use default debug loader outside of HTML documents."), a2.pause();
    }, goog.TransformedDependency = function(a2, b2, c, d, e) {
      goog.Dependency.call(this, a2, b2, c, d, e);
      this.contents_ = null;
      this.lazyFetch_ = !goog.inHtmlDocument_() || !("noModule" in goog.global.document.createElement("script"));
    }, goog.inherits(goog.TransformedDependency, goog.Dependency), goog.TransformedDependency.prototype.load = function(a2) {
      function b2() {
        e.contents_ = goog.loadFileSync_(e.path);
        e.contents_ && (e.contents_ = e.transform(e.contents_), e.contents_ && (e.contents_ += "\n//# sourceURL=" + e.path));
      }
      function c() {
        e.lazyFetch_ && b2();
        if (e.contents_) {
          f && a2.setModuleState(goog.ModuleType.ES6);
          try {
            var k = e.contents_;
            e.contents_ = null;
            goog.globalEval(goog.CLOSURE_EVAL_PREFILTER_.createScript(k));
            if (f) var n = goog.moduleLoaderState_.moduleName;
          } finally {
            f && a2.clearModuleState();
          }
          f && goog.global.$jscomp.require.ensure([e.getPathName()], function() {
            a2.registerEs6ModuleExports(e.path, goog.global.$jscomp.require(e.getPathName()), n);
          });
          a2.loaded();
        }
      }
      function d() {
        var k = goog.global.document, n = goog.Dependency.registerCallback_(function() {
          goog.Dependency.unregisterCallback_(n);
          c();
        }), m = goog.getScriptNonce_();
        m = "<script" + (m ? ' nonce="' + m + '"' : "") + ">" + goog.protectScriptTag_('goog.Dependency.callback_("' + n + '");') + "<\/script>";
        k.write(goog.TRUSTED_TYPES_POLICY_ ? goog.TRUSTED_TYPES_POLICY_.createHTML(m) : m);
      }
      var e = this;
      if (goog.global.CLOSURE_IMPORT_SCRIPT) b2(), this.contents_ && goog.global.CLOSURE_IMPORT_SCRIPT("", this.contents_) ? (this.contents_ = null, a2.loaded()) : a2.pause();
      else {
        var f = this.loadFlags.module == goog.ModuleType.ES6;
        this.lazyFetch_ || b2();
        var g = 1 < a2.pending().length;
        if (goog.Dependency.defer_ && (g || goog.isDocumentLoading_())) a2.defer(function() {
          c();
        });
        else {
          var h = goog.global.document;
          g = goog.inHtmlDocument_() && ("ActiveXObject" in goog.global || goog.isEdge_());
          if (f && goog.inHtmlDocument_() && goog.isDocumentLoading_() && !g) {
            goog.Dependency.defer_ = true;
            a2.pause();
            var l = h.onreadystatechange;
            h.onreadystatechange = function() {
              "interactive" == h.readyState && (h.onreadystatechange = l, c(), a2.resume());
              "function" === typeof l && l.apply(void 0, arguments);
            };
          } else goog.inHtmlDocument_() && goog.isDocumentLoading_() ? d() : c();
        }
      }
    }, goog.TransformedDependency.prototype.transform = function(a2) {
    }, goog.PreTranspiledEs6ModuleDependency = function(a2, b2, c, d, e) {
      goog.TransformedDependency.call(this, a2, b2, c, d, e);
    }, goog.inherits(goog.PreTranspiledEs6ModuleDependency, goog.TransformedDependency), goog.PreTranspiledEs6ModuleDependency.prototype.transform = function(a2) {
      return a2;
    }, goog.GoogModuleDependency = function(a2, b2, c, d, e) {
      goog.TransformedDependency.call(this, a2, b2, c, d, e);
    }, goog.inherits(goog.GoogModuleDependency, goog.TransformedDependency), goog.GoogModuleDependency.prototype.transform = function(a2) {
      return goog.LOAD_MODULE_USING_EVAL && void 0 !== goog.global.JSON ? "goog.loadModule(" + goog.global.JSON.stringify(a2 + "\n//# sourceURL=" + this.path + "\n") + ");" : 'goog.loadModule(function(exports) {"use strict";' + a2 + "\n;return exports});\n//# sourceURL=" + this.path + "\n";
    }, goog.DebugLoader_.prototype.addDependency = function(a2, b2, c, d) {
      b2 = b2 || [];
      a2 = a2.replace(/\\/g, "/");
      var e = goog.normalizePath_(goog.basePath + a2);
      d && "boolean" !== typeof d || (d = d ? { module: goog.ModuleType.GOOG } : {});
      c = this.factory_.createDependency(e, a2, b2, c, d);
      this.dependencies_[e] = c;
      for (c = 0; c < b2.length; c++) this.idToPath_[b2[c]] = e;
      this.idToPath_[a2] = e;
    }, goog.DependencyFactory = function() {
    }, goog.DependencyFactory.prototype.createDependency = function(a2, b2, c, d, e) {
      return e.module == goog.ModuleType.GOOG ? new goog.GoogModuleDependency(a2, b2, c, d, e) : e.module == goog.ModuleType.ES6 ? goog.ASSUME_ES_MODULES_TRANSPILED ? new goog.PreTranspiledEs6ModuleDependency(a2, b2, c, d, e) : new goog.Es6ModuleDependency(a2, b2, c, d, e) : new goog.Dependency(a2, b2, c, d, e);
    }, goog.debugLoader_ = new goog.DebugLoader_(), goog.loadClosureDeps = function() {
      goog.debugLoader_.loadClosureDeps();
    }, goog.setDependencyFactory = function(a2) {
      goog.debugLoader_.setDependencyFactory(a2);
    }, goog.TRUSTED_TYPES_POLICY_ = goog.TRUSTED_TYPES_POLICY_NAME ? goog.createTrustedTypesPolicy(goog.TRUSTED_TYPES_POLICY_NAME + "#base") : null, goog.global.CLOSURE_NO_DEPS || goog.debugLoader_.loadClosureDeps(), goog.bootstrap = function(a2, b2) {
      goog.debugLoader_.bootstrap(a2, b2);
    });
    if (!COMPILED) {
      isChrome87 = false;
      try {
        isChrome87 = eval(goog.global.trustedTypes.emptyScript) !== goog.global.trustedTypes.emptyScript;
      } catch (a2) {
      }
      goog.CLOSURE_EVAL_PREFILTER_ = goog.global.trustedTypes && isChrome87 && goog.createTrustedTypesPolicy("goog#base#devonly#eval") || { createScript: goog.identity_ };
    }
    var isChrome87;
    goog.object = {};
    function module$contents$goog$object_forEach(a2, b2, c) {
      for (const d in a2) b2.call(c, a2[d], d, a2);
    }
    function module$contents$goog$object_filter(a2, b2, c) {
      const d = {};
      for (const e in a2) b2.call(c, a2[e], e, a2) && (d[e] = a2[e]);
      return d;
    }
    function module$contents$goog$object_map(a2, b2, c) {
      const d = {};
      for (const e in a2) d[e] = b2.call(c, a2[e], e, a2);
      return d;
    }
    function module$contents$goog$object_some(a2, b2, c) {
      for (const d in a2) if (b2.call(c, a2[d], d, a2)) return true;
      return false;
    }
    function module$contents$goog$object_every(a2, b2, c) {
      for (const d in a2) if (!b2.call(c, a2[d], d, a2)) return false;
      return true;
    }
    function module$contents$goog$object_getCount(a2) {
      let b2 = 0;
      for (const c in a2) b2++;
      return b2;
    }
    function module$contents$goog$object_getAnyKey(a2) {
      for (const b2 in a2) return b2;
    }
    function module$contents$goog$object_getAnyValue(a2) {
      for (const b2 in a2) return a2[b2];
    }
    function module$contents$goog$object_contains(a2, b2) {
      return module$contents$goog$object_containsValue(a2, b2);
    }
    function module$contents$goog$object_getValues(a2) {
      const b2 = [];
      let c = 0;
      for (const d in a2) b2[c++] = a2[d];
      return b2;
    }
    function module$contents$goog$object_getKeys(a2) {
      const b2 = [];
      let c = 0;
      for (const d in a2) b2[c++] = d;
      return b2;
    }
    function module$contents$goog$object_getValueByKeys(a2, b2) {
      var c = goog.isArrayLike(b2);
      const d = c ? b2 : arguments;
      for (c = c ? 0 : 1; c < d.length; c++) {
        if (null == a2) return;
        a2 = a2[d[c]];
      }
      return a2;
    }
    function module$contents$goog$object_containsKey(a2, b2) {
      return null !== a2 && b2 in a2;
    }
    function module$contents$goog$object_containsValue(a2, b2) {
      for (const c in a2) if (a2[c] == b2) return true;
      return false;
    }
    function module$contents$goog$object_findKey(a2, b2, c) {
      for (const d in a2) if (b2.call(c, a2[d], d, a2)) return d;
    }
    function module$contents$goog$object_findValue(a2, b2, c) {
      return (b2 = module$contents$goog$object_findKey(a2, b2, c)) && a2[b2];
    }
    function module$contents$goog$object_isEmpty(a2) {
      for (const b2 in a2) return false;
      return true;
    }
    function module$contents$goog$object_clear(a2) {
      for (const b2 in a2) delete a2[b2];
    }
    function module$contents$goog$object_remove(a2, b2) {
      let c;
      (c = b2 in a2) && delete a2[b2];
      return c;
    }
    function module$contents$goog$object_add(a2, b2, c) {
      if (null !== a2 && b2 in a2) throw Error(`The object already contains the key "${b2}"`);
      module$contents$goog$object_set(a2, b2, c);
    }
    function module$contents$goog$object_get(a2, b2, c) {
      return null !== a2 && b2 in a2 ? a2[b2] : c;
    }
    function module$contents$goog$object_set(a2, b2, c) {
      a2[b2] = c;
    }
    function module$contents$goog$object_setIfUndefined(a2, b2, c) {
      return b2 in a2 ? a2[b2] : a2[b2] = c;
    }
    function module$contents$goog$object_setWithReturnValueIfNotSet(a2, b2, c) {
      if (b2 in a2) return a2[b2];
      c = c();
      return a2[b2] = c;
    }
    function module$contents$goog$object_equals(a2, b2) {
      for (const c in a2) if (!(c in b2) || a2[c] !== b2[c]) return false;
      for (const c in b2) if (!(c in a2)) return false;
      return true;
    }
    function module$contents$goog$object_clone(a2) {
      const b2 = {};
      for (const c in a2) b2[c] = a2[c];
      return b2;
    }
    function module$contents$goog$object_unsafeClone(a2) {
      if (!a2 || "object" !== typeof a2) return a2;
      if ("function" === typeof a2.clone) return a2.clone();
      if ("undefined" !== typeof Map && a2 instanceof Map) return new Map(a2);
      if ("undefined" !== typeof Set && a2 instanceof Set) return new Set(a2);
      if (a2 instanceof Date) return new Date(a2.getTime());
      const b2 = Array.isArray(a2) ? [] : "function" !== typeof ArrayBuffer || "function" !== typeof ArrayBuffer.isView || !ArrayBuffer.isView(a2) || a2 instanceof DataView ? {} : new a2.constructor(a2.length);
      for (const c in a2) b2[c] = module$contents$goog$object_unsafeClone(a2[c]);
      return b2;
    }
    function module$contents$goog$object_transpose(a2) {
      const b2 = {};
      for (const c in a2) b2[a2[c]] = c;
      return b2;
    }
    var module$contents$goog$object_PROTOTYPE_FIELDS = "constructor hasOwnProperty isPrototypeOf propertyIsEnumerable toLocaleString toString valueOf".split(" ");
    function module$contents$goog$object_extend(a2, b2) {
      let c, d;
      for (let e = 1; e < arguments.length; e++) {
        d = arguments[e];
        for (c in d) a2[c] = d[c];
        for (let f = 0; f < module$contents$goog$object_PROTOTYPE_FIELDS.length; f++) c = module$contents$goog$object_PROTOTYPE_FIELDS[f], Object.prototype.hasOwnProperty.call(d, c) && (a2[c] = d[c]);
      }
    }
    function module$contents$goog$object_create(a2) {
      const b2 = arguments.length;
      if (1 == b2 && Array.isArray(arguments[0])) return module$contents$goog$object_create.apply(null, arguments[0]);
      if (b2 % 2) throw Error("Uneven number of arguments");
      const c = {};
      for (let d = 0; d < b2; d += 2) c[arguments[d]] = arguments[d + 1];
      return c;
    }
    function module$contents$goog$object_createSet(a2) {
      const b2 = arguments.length;
      if (1 == b2 && Array.isArray(arguments[0])) return module$contents$goog$object_createSet.apply(null, arguments[0]);
      const c = {};
      for (let d = 0; d < b2; d++) c[arguments[d]] = true;
      return c;
    }
    function module$contents$goog$object_createImmutableView(a2) {
      let b2 = a2;
      Object.isFrozen && !Object.isFrozen(a2) && (b2 = Object.create(a2), Object.freeze(b2));
      return b2;
    }
    function module$contents$goog$object_isImmutableView(a2) {
      return !!Object.isFrozen && Object.isFrozen(a2);
    }
    function module$contents$goog$object_getAllPropertyNames(a2, b2, c) {
      if (!a2) return [];
      if (!Object.getOwnPropertyNames || !Object.getPrototypeOf) return module$contents$goog$object_getKeys(a2);
      const d = {};
      for (; a2 && (a2 !== Object.prototype || b2) && (a2 !== Function.prototype || c); ) {
        const e = Object.getOwnPropertyNames(a2);
        for (let f = 0; f < e.length; f++) d[e[f]] = true;
        a2 = Object.getPrototypeOf(a2);
      }
      return module$contents$goog$object_getKeys(d);
    }
    function module$contents$goog$object_getSuperClass(a2) {
      return (a2 = Object.getPrototypeOf(a2.prototype)) && a2.constructor;
    }
    goog.object.add = module$contents$goog$object_add;
    goog.object.clear = module$contents$goog$object_clear;
    goog.object.clone = module$contents$goog$object_clone;
    goog.object.contains = module$contents$goog$object_contains;
    goog.object.containsKey = module$contents$goog$object_containsKey;
    goog.object.containsValue = module$contents$goog$object_containsValue;
    goog.object.create = module$contents$goog$object_create;
    goog.object.createImmutableView = module$contents$goog$object_createImmutableView;
    goog.object.createSet = module$contents$goog$object_createSet;
    goog.object.equals = module$contents$goog$object_equals;
    goog.object.every = module$contents$goog$object_every;
    goog.object.extend = module$contents$goog$object_extend;
    goog.object.filter = module$contents$goog$object_filter;
    goog.object.findKey = module$contents$goog$object_findKey;
    goog.object.findValue = module$contents$goog$object_findValue;
    goog.object.forEach = module$contents$goog$object_forEach;
    goog.object.get = module$contents$goog$object_get;
    goog.object.getAllPropertyNames = module$contents$goog$object_getAllPropertyNames;
    goog.object.getAnyKey = module$contents$goog$object_getAnyKey;
    goog.object.getAnyValue = module$contents$goog$object_getAnyValue;
    goog.object.getCount = module$contents$goog$object_getCount;
    goog.object.getKeys = module$contents$goog$object_getKeys;
    goog.object.getSuperClass = module$contents$goog$object_getSuperClass;
    goog.object.getValueByKeys = module$contents$goog$object_getValueByKeys;
    goog.object.getValues = module$contents$goog$object_getValues;
    goog.object.isEmpty = module$contents$goog$object_isEmpty;
    goog.object.isImmutableView = module$contents$goog$object_isImmutableView;
    goog.object.map = module$contents$goog$object_map;
    goog.object.remove = module$contents$goog$object_remove;
    goog.object.set = module$contents$goog$object_set;
    goog.object.setIfUndefined = module$contents$goog$object_setIfUndefined;
    goog.object.setWithReturnValueIfNotSet = module$contents$goog$object_setWithReturnValueIfNotSet;
    goog.object.some = module$contents$goog$object_some;
    goog.object.transpose = module$contents$goog$object_transpose;
    goog.object.unsafeClone = module$contents$goog$object_unsafeClone;
    goog.debug = {};
    function module$contents$goog$debug$Error_DebugError(a2, b2) {
      if (Error.captureStackTrace) Error.captureStackTrace(this, module$contents$goog$debug$Error_DebugError);
      else {
        const c = Error().stack;
        c && (this.stack = c);
      }
      a2 && (this.message = String(a2));
      void 0 !== b2 && (this.cause = b2);
      this.reportErrorToServer = true;
    }
    goog.inherits(module$contents$goog$debug$Error_DebugError, Error);
    module$contents$goog$debug$Error_DebugError.prototype.name = "CustomError";
    goog.debug.Error = module$contents$goog$debug$Error_DebugError;
    goog.dom = {};
    goog.dom.NodeType = { ELEMENT: 1, ATTRIBUTE: 2, TEXT: 3, CDATA_SECTION: 4, ENTITY_REFERENCE: 5, ENTITY: 6, PROCESSING_INSTRUCTION: 7, COMMENT: 8, DOCUMENT: 9, DOCUMENT_TYPE: 10, DOCUMENT_FRAGMENT: 11, NOTATION: 12 };
    goog.asserts = {};
    goog.asserts.ENABLE_ASSERTS = goog.DEBUG;
    function module$contents$goog$asserts_AssertionError(a2, b2) {
      module$contents$goog$debug$Error_DebugError.call(this, module$contents$goog$asserts_subs(a2, b2));
      this.messagePattern = a2;
    }
    goog.inherits(module$contents$goog$asserts_AssertionError, module$contents$goog$debug$Error_DebugError);
    goog.asserts.AssertionError = module$contents$goog$asserts_AssertionError;
    module$contents$goog$asserts_AssertionError.prototype.name = "AssertionError";
    goog.asserts.DEFAULT_ERROR_HANDLER = function(a2) {
      throw a2;
    };
    var module$contents$goog$asserts_errorHandler_ = goog.asserts.DEFAULT_ERROR_HANDLER;
    function module$contents$goog$asserts_subs(a2, b2) {
      a2 = a2.split("%s");
      let c = "";
      const d = a2.length - 1;
      for (let e = 0; e < d; e++) c += a2[e] + (e < b2.length ? b2[e] : "%s");
      return c + a2[d];
    }
    function module$contents$goog$asserts_doAssertFailure(a2, b2, c, d) {
      let e = "Assertion failed", f;
      c ? (e += ": " + c, f = d) : a2 && (e += ": " + a2, f = b2);
      a2 = new module$contents$goog$asserts_AssertionError("" + e, f || []);
      module$contents$goog$asserts_errorHandler_(a2);
    }
    goog.asserts.setErrorHandler = function(a2) {
      goog.asserts.ENABLE_ASSERTS && (module$contents$goog$asserts_errorHandler_ = a2);
    };
    goog.asserts.assert = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && !a2 && module$contents$goog$asserts_doAssertFailure("", null, b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertExists = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && null == a2 && module$contents$goog$asserts_doAssertFailure("Expected to exist: %s.", [a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.fail = function(a2, b2) {
      goog.asserts.ENABLE_ASSERTS && module$contents$goog$asserts_errorHandler_(new module$contents$goog$asserts_AssertionError("Failure" + (a2 ? ": " + a2 : ""), Array.prototype.slice.call(arguments, 1)));
    };
    goog.asserts.assertNumber = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && "number" !== typeof a2 && module$contents$goog$asserts_doAssertFailure("Expected number but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertString = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && "string" !== typeof a2 && module$contents$goog$asserts_doAssertFailure("Expected string but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertFunction = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && "function" !== typeof a2 && module$contents$goog$asserts_doAssertFailure("Expected function but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertObject = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && !goog.isObject(a2) && module$contents$goog$asserts_doAssertFailure("Expected object but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertArray = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && !Array.isArray(a2) && module$contents$goog$asserts_doAssertFailure("Expected array but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertBoolean = function(a2, b2, c) {
      goog.asserts.ENABLE_ASSERTS && "boolean" !== typeof a2 && module$contents$goog$asserts_doAssertFailure("Expected boolean but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertElement = function(a2, b2, c) {
      !goog.asserts.ENABLE_ASSERTS || goog.isObject(a2) && a2.nodeType == goog.dom.NodeType.ELEMENT || module$contents$goog$asserts_doAssertFailure("Expected Element but got %s: %s.", [goog.typeOf(a2), a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    goog.asserts.assertInstanceof = function(a2, b2, c, d) {
      !goog.asserts.ENABLE_ASSERTS || a2 instanceof b2 || module$contents$goog$asserts_doAssertFailure("Expected instanceof %s but got %s.", [module$contents$goog$asserts_getType(b2), module$contents$goog$asserts_getType(a2)], c, Array.prototype.slice.call(arguments, 3));
      return a2;
    };
    goog.asserts.assertFinite = function(a2, b2, c) {
      !goog.asserts.ENABLE_ASSERTS || "number" == typeof a2 && isFinite(a2) || module$contents$goog$asserts_doAssertFailure("Expected %s to be a finite number but it is not.", [a2], b2, Array.prototype.slice.call(arguments, 2));
      return a2;
    };
    function module$contents$goog$asserts_getType(a2) {
      return a2 instanceof Function ? a2.displayName || a2.name || "unknown type name" : a2 instanceof Object ? a2.constructor.displayName || a2.constructor.name || Object.prototype.toString.call(a2) : null === a2 ? "null" : typeof a2;
    }
    goog.array = {};
    goog.NATIVE_ARRAY_PROTOTYPES = goog.TRUSTED_SITE;
    var module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS = 2012 < goog.FEATURESET_YEAR;
    goog.array.ASSUME_NATIVE_FUNCTIONS = module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS;
    function module$contents$goog$array_peek(a2) {
      return a2[a2.length - 1];
    }
    goog.array.peek = module$contents$goog$array_peek;
    goog.array.last = module$contents$goog$array_peek;
    var module$contents$goog$array_indexOf = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.indexOf) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.indexOf.call(a2, b2, c);
    } : function(a2, b2, c) {
      c = null == c ? 0 : 0 > c ? Math.max(0, a2.length + c) : c;
      if ("string" === typeof a2) return "string" !== typeof b2 || 1 != b2.length ? -1 : a2.indexOf(b2, c);
      for (; c < a2.length; c++) if (c in a2 && a2[c] === b2) return c;
      return -1;
    };
    goog.array.indexOf = module$contents$goog$array_indexOf;
    var module$contents$goog$array_lastIndexOf = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.lastIndexOf) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.lastIndexOf.call(a2, b2, null == c ? a2.length - 1 : c);
    } : function(a2, b2, c) {
      c = null == c ? a2.length - 1 : c;
      0 > c && (c = Math.max(0, a2.length + c));
      if ("string" === typeof a2) return "string" !== typeof b2 || 1 != b2.length ? -1 : a2.lastIndexOf(b2, c);
      for (; 0 <= c; c--) if (c in a2 && a2[c] === b2) return c;
      return -1;
    };
    goog.array.lastIndexOf = module$contents$goog$array_lastIndexOf;
    var module$contents$goog$array_forEach = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.forEach) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      Array.prototype.forEach.call(a2, b2, c);
    } : function(a2, b2, c) {
      const d = a2.length, e = "string" === typeof a2 ? a2.split("") : a2;
      for (let f = 0; f < d; f++) f in e && b2.call(c, e[f], f, a2);
    };
    goog.array.forEach = module$contents$goog$array_forEach;
    function module$contents$goog$array_forEachRight(a2, b2, c) {
      var d = a2.length;
      const e = "string" === typeof a2 ? a2.split("") : a2;
      for (--d; 0 <= d; --d) d in e && b2.call(c, e[d], d, a2);
    }
    goog.array.forEachRight = module$contents$goog$array_forEachRight;
    var module$contents$goog$array_filter = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.filter) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.filter.call(a2, b2, c);
    } : function(a2, b2, c) {
      const d = a2.length, e = [];
      let f = 0;
      const g = "string" === typeof a2 ? a2.split("") : a2;
      for (let h = 0; h < d; h++) if (h in g) {
        const l = g[h];
        b2.call(c, l, h, a2) && (e[f++] = l);
      }
      return e;
    };
    goog.array.filter = module$contents$goog$array_filter;
    var module$contents$goog$array_map = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.map) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.map.call(a2, b2, c);
    } : function(a2, b2, c) {
      const d = a2.length, e = Array(d), f = "string" === typeof a2 ? a2.split("") : a2;
      for (let g = 0; g < d; g++) g in f && (e[g] = b2.call(c, f[g], g, a2));
      return e;
    };
    goog.array.map = module$contents$goog$array_map;
    var module$contents$goog$array_reduce = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.reduce) ? function(a2, b2, c, d) {
      goog.asserts.assert(null != a2.length);
      d && (b2 = goog.bind(b2, d));
      return Array.prototype.reduce.call(a2, b2, c);
    } : function(a2, b2, c, d) {
      let e = c;
      module$contents$goog$array_forEach(a2, function(f, g) {
        e = b2.call(d, e, f, g, a2);
      });
      return e;
    };
    goog.array.reduce = module$contents$goog$array_reduce;
    var module$contents$goog$array_reduceRight = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.reduceRight) ? function(a2, b2, c, d) {
      goog.asserts.assert(null != a2.length);
      goog.asserts.assert(null != b2);
      d && (b2 = goog.bind(b2, d));
      return Array.prototype.reduceRight.call(a2, b2, c);
    } : function(a2, b2, c, d) {
      let e = c;
      module$contents$goog$array_forEachRight(a2, function(f, g) {
        e = b2.call(d, e, f, g, a2);
      });
      return e;
    };
    goog.array.reduceRight = module$contents$goog$array_reduceRight;
    var module$contents$goog$array_some = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.some) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.some.call(a2, b2, c);
    } : function(a2, b2, c) {
      const d = a2.length, e = "string" === typeof a2 ? a2.split("") : a2;
      for (let f = 0; f < d; f++) if (f in e && b2.call(c, e[f], f, a2)) return true;
      return false;
    };
    goog.array.some = module$contents$goog$array_some;
    var module$contents$goog$array_every = goog.NATIVE_ARRAY_PROTOTYPES && (module$contents$goog$array_ASSUME_NATIVE_FUNCTIONS || Array.prototype.every) ? function(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.every.call(a2, b2, c);
    } : function(a2, b2, c) {
      const d = a2.length, e = "string" === typeof a2 ? a2.split("") : a2;
      for (let f = 0; f < d; f++) if (f in e && !b2.call(c, e[f], f, a2)) return false;
      return true;
    };
    goog.array.every = module$contents$goog$array_every;
    function module$contents$goog$array_count(a2, b2, c) {
      let d = 0;
      module$contents$goog$array_forEach(a2, function(e, f, g) {
        b2.call(c, e, f, g) && ++d;
      }, c);
      return d;
    }
    goog.array.count = module$contents$goog$array_count;
    function module$contents$goog$array_find(a2, b2, c) {
      b2 = module$contents$goog$array_findIndex(a2, b2, c);
      return 0 > b2 ? null : "string" === typeof a2 ? a2.charAt(b2) : a2[b2];
    }
    goog.array.find = module$contents$goog$array_find;
    function module$contents$goog$array_findIndex(a2, b2, c) {
      const d = a2.length, e = "string" === typeof a2 ? a2.split("") : a2;
      for (let f = 0; f < d; f++) if (f in e && b2.call(c, e[f], f, a2)) return f;
      return -1;
    }
    goog.array.findIndex = module$contents$goog$array_findIndex;
    function module$contents$goog$array_findRight(a2, b2, c) {
      b2 = module$contents$goog$array_findIndexRight(a2, b2, c);
      return 0 > b2 ? null : "string" === typeof a2 ? a2.charAt(b2) : a2[b2];
    }
    goog.array.findRight = module$contents$goog$array_findRight;
    function module$contents$goog$array_findIndexRight(a2, b2, c) {
      var d = a2.length;
      const e = "string" === typeof a2 ? a2.split("") : a2;
      for (--d; 0 <= d; d--) if (d in e && b2.call(c, e[d], d, a2)) return d;
      return -1;
    }
    goog.array.findIndexRight = module$contents$goog$array_findIndexRight;
    function module$contents$goog$array_contains(a2, b2) {
      return 0 <= module$contents$goog$array_indexOf(a2, b2);
    }
    goog.array.contains = module$contents$goog$array_contains;
    function module$contents$goog$array_isEmpty(a2) {
      return 0 == a2.length;
    }
    goog.array.isEmpty = module$contents$goog$array_isEmpty;
    function module$contents$goog$array_clear(a2) {
      if (!Array.isArray(a2)) for (let b2 = a2.length - 1; 0 <= b2; b2--) delete a2[b2];
      a2.length = 0;
    }
    goog.array.clear = module$contents$goog$array_clear;
    function module$contents$goog$array_insert(a2, b2) {
      module$contents$goog$array_contains(a2, b2) || a2.push(b2);
    }
    goog.array.insert = module$contents$goog$array_insert;
    function module$contents$goog$array_insertAt(a2, b2, c) {
      module$contents$goog$array_splice(a2, c, 0, b2);
    }
    goog.array.insertAt = module$contents$goog$array_insertAt;
    function module$contents$goog$array_insertArrayAt(a2, b2, c) {
      goog.partial(module$contents$goog$array_splice, a2, c, 0).apply(null, b2);
    }
    goog.array.insertArrayAt = module$contents$goog$array_insertArrayAt;
    function module$contents$goog$array_insertBefore(a2, b2, c) {
      let d;
      2 == arguments.length || 0 > (d = module$contents$goog$array_indexOf(a2, c)) ? a2.push(b2) : module$contents$goog$array_insertAt(a2, b2, d);
    }
    goog.array.insertBefore = module$contents$goog$array_insertBefore;
    function module$contents$goog$array_remove(a2, b2) {
      b2 = module$contents$goog$array_indexOf(a2, b2);
      let c;
      (c = 0 <= b2) && module$contents$goog$array_removeAt(a2, b2);
      return c;
    }
    goog.array.remove = module$contents$goog$array_remove;
    function module$contents$goog$array_removeLast(a2, b2) {
      b2 = module$contents$goog$array_lastIndexOf(a2, b2);
      return 0 <= b2 ? (module$contents$goog$array_removeAt(a2, b2), true) : false;
    }
    goog.array.removeLast = module$contents$goog$array_removeLast;
    function module$contents$goog$array_removeAt(a2, b2) {
      goog.asserts.assert(null != a2.length);
      return 1 == Array.prototype.splice.call(a2, b2, 1).length;
    }
    goog.array.removeAt = module$contents$goog$array_removeAt;
    function module$contents$goog$array_removeIf(a2, b2, c) {
      b2 = module$contents$goog$array_findIndex(a2, b2, c);
      return 0 <= b2 ? (module$contents$goog$array_removeAt(a2, b2), true) : false;
    }
    goog.array.removeIf = module$contents$goog$array_removeIf;
    function module$contents$goog$array_removeAllIf(a2, b2, c) {
      let d = 0;
      module$contents$goog$array_forEachRight(a2, function(e, f) {
        b2.call(c, e, f, a2) && module$contents$goog$array_removeAt(a2, f) && d++;
      });
      return d;
    }
    goog.array.removeAllIf = module$contents$goog$array_removeAllIf;
    function module$contents$goog$array_concat(a2) {
      return Array.prototype.concat.apply([], arguments);
    }
    goog.array.concat = module$contents$goog$array_concat;
    function module$contents$goog$array_join(a2) {
      return Array.prototype.concat.apply([], arguments);
    }
    goog.array.join = module$contents$goog$array_join;
    function module$contents$goog$array_toArray(a2) {
      const b2 = a2.length;
      if (0 < b2) {
        const c = Array(b2);
        for (let d = 0; d < b2; d++) c[d] = a2[d];
        return c;
      }
      return [];
    }
    var module$contents$goog$array_clone = goog.array.toArray = module$contents$goog$array_toArray;
    goog.array.clone = module$contents$goog$array_toArray;
    function module$contents$goog$array_extend(a2, b2) {
      for (let c = 1; c < arguments.length; c++) {
        const d = arguments[c];
        if (goog.isArrayLike(d)) {
          const e = a2.length || 0, f = d.length || 0;
          a2.length = e + f;
          for (let g = 0; g < f; g++) a2[e + g] = d[g];
        } else a2.push(d);
      }
    }
    goog.array.extend = module$contents$goog$array_extend;
    function module$contents$goog$array_splice(a2, b2, c, d) {
      goog.asserts.assert(null != a2.length);
      return Array.prototype.splice.apply(a2, module$contents$goog$array_slice(arguments, 1));
    }
    goog.array.splice = module$contents$goog$array_splice;
    function module$contents$goog$array_slice(a2, b2, c) {
      goog.asserts.assert(null != a2.length);
      return 2 >= arguments.length ? Array.prototype.slice.call(a2, b2) : Array.prototype.slice.call(a2, b2, c);
    }
    goog.array.slice = module$contents$goog$array_slice;
    function module$contents$goog$array_removeDuplicates(a2, b2, c) {
      b2 = b2 || a2;
      var d = function(g) {
        return goog.isObject(g) ? "o" + goog.getUid(g) : (typeof g).charAt(0) + g;
      };
      c = c || d;
      let e = d = 0;
      const f = {};
      for (; e < a2.length; ) {
        const g = a2[e++], h = c(g);
        Object.prototype.hasOwnProperty.call(f, h) || (f[h] = true, b2[d++] = g);
      }
      b2.length = d;
    }
    goog.array.removeDuplicates = module$contents$goog$array_removeDuplicates;
    function module$contents$goog$array_binarySearch(a2, b2, c) {
      return module$contents$goog$array_binarySearch_(a2, c || module$contents$goog$array_defaultCompare, false, b2);
    }
    goog.array.binarySearch = module$contents$goog$array_binarySearch;
    function module$contents$goog$array_binarySelect(a2, b2, c) {
      return module$contents$goog$array_binarySearch_(a2, b2, true, void 0, c);
    }
    goog.array.binarySelect = module$contents$goog$array_binarySelect;
    function module$contents$goog$array_binarySearch_(a2, b2, c, d, e) {
      let f = 0, g = a2.length, h;
      for (; f < g; ) {
        const l = f + (g - f >>> 1);
        let k;
        k = c ? b2.call(e, a2[l], l, a2) : b2(d, a2[l]);
        0 < k ? f = l + 1 : (g = l, h = !k);
      }
      return h ? f : -f - 1;
    }
    function module$contents$goog$array_sort(a2, b2) {
      a2.sort(b2 || module$contents$goog$array_defaultCompare);
    }
    goog.array.sort = module$contents$goog$array_sort;
    function module$contents$goog$array_stableSort(a2, b2) {
      const c = Array(a2.length);
      for (let e = 0; e < a2.length; e++) c[e] = { index: e, value: a2[e] };
      const d = b2 || module$contents$goog$array_defaultCompare;
      module$contents$goog$array_sort(c, function(e, f) {
        return d(e.value, f.value) || e.index - f.index;
      });
      for (b2 = 0; b2 < a2.length; b2++) a2[b2] = c[b2].value;
    }
    goog.array.stableSort = module$contents$goog$array_stableSort;
    function module$contents$goog$array_sortByKey(a2, b2, c) {
      const d = c || module$contents$goog$array_defaultCompare;
      module$contents$goog$array_sort(a2, function(e, f) {
        return d(b2(e), b2(f));
      });
    }
    goog.array.sortByKey = module$contents$goog$array_sortByKey;
    function module$contents$goog$array_sortObjectsByKey(a2, b2, c) {
      module$contents$goog$array_sortByKey(a2, function(d) {
        return d[b2];
      }, c);
    }
    goog.array.sortObjectsByKey = module$contents$goog$array_sortObjectsByKey;
    function module$contents$goog$array_isSorted(a2, b2, c) {
      b2 = b2 || module$contents$goog$array_defaultCompare;
      for (let d = 1; d < a2.length; d++) {
        const e = b2(a2[d - 1], a2[d]);
        if (0 < e || 0 == e && c) return false;
      }
      return true;
    }
    goog.array.isSorted = module$contents$goog$array_isSorted;
    function module$contents$goog$array_equals(a2, b2, c) {
      if (!goog.isArrayLike(a2) || !goog.isArrayLike(b2) || a2.length != b2.length) return false;
      const d = a2.length;
      c = c || module$contents$goog$array_defaultCompareEquality;
      for (let e = 0; e < d; e++) if (!c(a2[e], b2[e])) return false;
      return true;
    }
    goog.array.equals = module$contents$goog$array_equals;
    function module$contents$goog$array_compare3(a2, b2, c) {
      c = c || module$contents$goog$array_defaultCompare;
      const d = Math.min(a2.length, b2.length);
      for (let e = 0; e < d; e++) {
        const f = c(a2[e], b2[e]);
        if (0 != f) return f;
      }
      return module$contents$goog$array_defaultCompare(a2.length, b2.length);
    }
    goog.array.compare3 = module$contents$goog$array_compare3;
    function module$contents$goog$array_defaultCompare(a2, b2) {
      return a2 > b2 ? 1 : a2 < b2 ? -1 : 0;
    }
    goog.array.defaultCompare = module$contents$goog$array_defaultCompare;
    function module$contents$goog$array_inverseDefaultCompare(a2, b2) {
      return -module$contents$goog$array_defaultCompare(a2, b2);
    }
    goog.array.inverseDefaultCompare = module$contents$goog$array_inverseDefaultCompare;
    function module$contents$goog$array_defaultCompareEquality(a2, b2) {
      return a2 === b2;
    }
    goog.array.defaultCompareEquality = module$contents$goog$array_defaultCompareEquality;
    function module$contents$goog$array_binaryInsert(a2, b2, c) {
      c = module$contents$goog$array_binarySearch(a2, b2, c);
      return 0 > c ? (module$contents$goog$array_insertAt(a2, b2, -(c + 1)), true) : false;
    }
    goog.array.binaryInsert = module$contents$goog$array_binaryInsert;
    function module$contents$goog$array_binaryRemove(a2, b2, c) {
      b2 = module$contents$goog$array_binarySearch(a2, b2, c);
      return 0 <= b2 ? module$contents$goog$array_removeAt(a2, b2) : false;
    }
    goog.array.binaryRemove = module$contents$goog$array_binaryRemove;
    function module$contents$goog$array_bucket(a2, b2, c) {
      const d = {};
      for (let e = 0; e < a2.length; e++) {
        const f = a2[e], g = b2.call(c, f, e, a2);
        void 0 !== g && (d[g] || (d[g] = [])).push(f);
      }
      return d;
    }
    goog.array.bucket = module$contents$goog$array_bucket;
    function module$contents$goog$array_bucketToMap(a2, b2) {
      const c = /* @__PURE__ */ new Map();
      for (let d = 0; d < a2.length; d++) {
        const e = a2[d], f = b2(e, d, a2);
        if (void 0 !== f) {
          let g = c.get(f);
          g || (g = [], c.set(f, g));
          g.push(e);
        }
      }
      return c;
    }
    goog.array.bucketToMap = module$contents$goog$array_bucketToMap;
    function module$contents$goog$array_toObject(a2, b2, c) {
      const d = {};
      module$contents$goog$array_forEach(a2, function(e, f) {
        d[b2.call(c, e, f, a2)] = e;
      });
      return d;
    }
    goog.array.toObject = module$contents$goog$array_toObject;
    function module$contents$goog$array_toMap(a2, b2) {
      const c = /* @__PURE__ */ new Map();
      for (let d = 0; d < a2.length; d++) {
        const e = a2[d];
        c.set(b2(e, d, a2), e);
      }
      return c;
    }
    goog.array.toMap = module$contents$goog$array_toMap;
    function module$contents$goog$array_range(a2, b2, c) {
      const d = [];
      let e = 0, f = a2;
      c = c || 1;
      void 0 !== b2 && (e = a2, f = b2);
      if (0 > c * (f - e)) return [];
      if (0 < c) for (a2 = e; a2 < f; a2 += c) d.push(a2);
      else for (a2 = e; a2 > f; a2 += c) d.push(a2);
      return d;
    }
    goog.array.range = module$contents$goog$array_range;
    function module$contents$goog$array_repeat(a2, b2) {
      const c = [];
      for (let d = 0; d < b2; d++) c[d] = a2;
      return c;
    }
    goog.array.repeat = module$contents$goog$array_repeat;
    function module$contents$goog$array_flatten(a2) {
      const b2 = [];
      for (let d = 0; d < arguments.length; d++) {
        const e = arguments[d];
        if (Array.isArray(e)) for (let f = 0; f < e.length; f += 8192) {
          var c = module$contents$goog$array_slice(e, f, f + 8192);
          c = module$contents$goog$array_flatten.apply(null, c);
          for (let g = 0; g < c.length; g++) b2.push(c[g]);
        }
        else b2.push(e);
      }
      return b2;
    }
    goog.array.flatten = module$contents$goog$array_flatten;
    function module$contents$goog$array_rotate(a2, b2) {
      goog.asserts.assert(null != a2.length);
      a2.length && (b2 %= a2.length, 0 < b2 ? Array.prototype.unshift.apply(a2, a2.splice(-b2, b2)) : 0 > b2 && Array.prototype.push.apply(a2, a2.splice(0, -b2)));
      return a2;
    }
    goog.array.rotate = module$contents$goog$array_rotate;
    function module$contents$goog$array_moveItem(a2, b2, c) {
      goog.asserts.assert(0 <= b2 && b2 < a2.length);
      goog.asserts.assert(0 <= c && c < a2.length);
      b2 = Array.prototype.splice.call(a2, b2, 1);
      Array.prototype.splice.call(a2, c, 0, b2[0]);
    }
    goog.array.moveItem = module$contents$goog$array_moveItem;
    function module$contents$goog$array_zip(a2) {
      if (!arguments.length) return [];
      const b2 = [];
      let c = arguments[0].length;
      for (var d = 1; d < arguments.length; d++) arguments[d].length < c && (c = arguments[d].length);
      for (d = 0; d < c; d++) {
        const e = [];
        for (let f = 0; f < arguments.length; f++) e.push(arguments[f][d]);
        b2.push(e);
      }
      return b2;
    }
    goog.array.zip = module$contents$goog$array_zip;
    function module$contents$goog$array_shuffle(a2, b2) {
      b2 = b2 || Math.random;
      for (let c = a2.length - 1; 0 < c; c--) {
        const d = Math.floor(b2() * (c + 1)), e = a2[c];
        a2[c] = a2[d];
        a2[d] = e;
      }
    }
    goog.array.shuffle = module$contents$goog$array_shuffle;
    function module$contents$goog$array_copyByIndex(a2, b2) {
      const c = [];
      module$contents$goog$array_forEach(b2, function(d) {
        c.push(a2[d]);
      });
      return c;
    }
    goog.array.copyByIndex = module$contents$goog$array_copyByIndex;
    function module$contents$goog$array_concatMap(a2, b2, c) {
      return module$contents$goog$array_concat.apply([], module$contents$goog$array_map(a2, b2, c));
    }
    goog.array.concatMap = module$contents$goog$array_concatMap;
    var jspb = { asserts: {} };
    function module$contents$jspb$asserts_doAssertFailure(a2, b2, c, d) {
      let e = "Assertion failed", f;
      c ? (e += ": " + c, f = d) : a2 && (e += ": " + a2, f = b2);
      throw Error("" + e, f || []);
    }
    function module$contents$jspb$asserts_assert(a2, b2, ...c) {
      a2 || module$contents$jspb$asserts_doAssertFailure("", null, b2, c);
      return a2;
    }
    function module$contents$jspb$asserts_assertString(a2, b2, ...c) {
      "string" !== typeof a2 && module$contents$jspb$asserts_doAssertFailure("Expected string but got %s: %s.", [goog.typeOf(a2), a2], b2, c);
      return a2;
    }
    function module$contents$jspb$asserts_assertArray(a2, b2, ...c) {
      Array.isArray(a2) || module$contents$jspb$asserts_doAssertFailure("Expected array but got %s: %s.", [goog.typeOf(a2), a2], b2, c);
      return a2;
    }
    function module$contents$jspb$asserts_fail(a2, ...b2) {
      throw Error("Failure" + (a2 ? ": " + a2 : ""), b2);
    }
    function module$contents$jspb$asserts_assertInstanceof(a2, b2, c, ...d) {
      a2 instanceof b2 || module$contents$jspb$asserts_doAssertFailure("Expected instanceof %s but got %s.", [module$contents$jspb$asserts_getType(b2), module$contents$jspb$asserts_getType(a2)], c, d);
      return a2;
    }
    function module$contents$jspb$asserts_getType(a2) {
      return a2 instanceof Function ? a2.displayName || a2.name || "unknown type name" : a2 instanceof Object ? a2.constructor.displayName || a2.constructor.name || Object.prototype.toString.call(a2) : null === a2 ? "null" : typeof a2;
    }
    jspb.asserts.doAssertFailure = module$contents$jspb$asserts_doAssertFailure;
    jspb.asserts.assert = module$contents$jspb$asserts_assert;
    jspb.asserts.assertString = module$contents$jspb$asserts_assertString;
    jspb.asserts.assertArray = module$contents$jspb$asserts_assertArray;
    jspb.asserts.fail = module$contents$jspb$asserts_fail;
    jspb.asserts.assertInstanceof = module$contents$jspb$asserts_assertInstanceof;
    jspb.asserts.getType = module$contents$jspb$asserts_getType;
    var module$contents$jspb$Map_Map = function(a2, b2) {
      this.arr_ = a2;
      this.valueCtor_ = b2;
      this.map_ = {};
      this.arrClean = true;
      0 < this.arr_.length && this.loadFromArray_();
    };
    var module$contents$jspb$Map_Entry_ = function(a2, b2) {
      this.key = a2;
      this.value = b2;
      this.valueWrapper = void 0;
    };
    module$contents$jspb$Map_Map.prototype.loadFromArray_ = function() {
      for (var a2 = 0; a2 < this.arr_.length; a2++) {
        var b2 = this.arr_[a2], c = b2[0];
        this.map_[c.toString()] = new module$contents$jspb$Map_Entry_(c, b2[1]);
      }
      this.arrClean = true;
    };
    module$contents$jspb$Map_Map.prototype.toArray = function() {
      if (this.arrClean) {
        if (this.valueCtor_) {
          var a2 = this.map_, b2;
          for (b2 in a2) if (Object.prototype.hasOwnProperty.call(a2, b2)) {
            var c = a2[b2].valueWrapper;
            c && c.toArray();
          }
        }
      } else {
        this.arr_.length = 0;
        a2 = this.stringKeys_();
        a2.sort();
        for (b2 = 0; b2 < a2.length; b2++) {
          var d = this.map_[a2[b2]];
          (c = d.valueWrapper) && c.toArray();
          this.arr_.push([d.key, d.value]);
        }
        this.arrClean = true;
      }
      return this.arr_;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "toArray", module$contents$jspb$Map_Map.prototype.toArray);
    module$contents$jspb$Map_Map.prototype.toObject = function(a2, b2) {
      for (var c = this.toArray(), d = [], e = 0; e < c.length; e++) {
        var f = this.map_[c[e][0].toString()];
        this.wrapEntry_(f);
        var g = f.valueWrapper;
        g ? (module$contents$jspb$asserts_assert(b2), d.push([f.key, b2(a2, g)])) : d.push([f.key, f.value]);
      }
      return d;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "toObject", module$contents$jspb$Map_Map.prototype.toObject);
    module$contents$jspb$Map_Map.fromObject = function(a2, b2, c) {
      b2 = new module$contents$jspb$Map_Map([], b2);
      for (var d = 0; d < a2.length; d++) {
        var e = a2[d][0], f = c(a2[d][1]);
        b2.set(e, f);
      }
      return b2;
    };
    goog.exportSymbol("module$contents$jspb$Map_Map.fromObject", module$contents$jspb$Map_Map.fromObject);
    var module$contents$jspb$Map_ArrayIteratorIterable_ = function(a2) {
      this.idx_ = 0;
      this.arr_ = a2;
    };
    module$contents$jspb$Map_ArrayIteratorIterable_.prototype.next = function() {
      return this.idx_ < this.arr_.length ? { done: false, value: this.arr_[this.idx_++] } : { done: true, value: void 0 };
    };
    "undefined" != typeof Symbol && (module$contents$jspb$Map_ArrayIteratorIterable_.prototype[Symbol.iterator] = function() {
      return this;
    });
    module$contents$jspb$Map_Map.prototype.getLength = function() {
      return this.stringKeys_().length;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "getLength", module$contents$jspb$Map_Map.prototype.getLength);
    module$contents$jspb$Map_Map.prototype.clear = function() {
      this.map_ = {};
      this.arrClean = false;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "clear", module$contents$jspb$Map_Map.prototype.clear);
    module$contents$jspb$Map_Map.prototype.del = function(a2) {
      a2 = a2.toString();
      var b2 = this.map_.hasOwnProperty(a2);
      delete this.map_[a2];
      this.arrClean = false;
      return b2;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "del", module$contents$jspb$Map_Map.prototype.del);
    module$contents$jspb$Map_Map.prototype.getEntryList = function() {
      var a2 = [], b2 = this.stringKeys_();
      b2.sort();
      for (var c = 0; c < b2.length; c++) {
        var d = this.map_[b2[c]];
        a2.push([d.key, d.value]);
      }
      return a2;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "getEntryList", module$contents$jspb$Map_Map.prototype.getEntryList);
    module$contents$jspb$Map_Map.prototype.entries = function() {
      var a2 = [], b2 = this.stringKeys_();
      b2.sort();
      for (var c = 0; c < b2.length; c++) {
        var d = this.map_[b2[c]];
        a2.push([d.key, this.wrapEntry_(d)]);
      }
      return new module$contents$jspb$Map_ArrayIteratorIterable_(a2);
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "entries", module$contents$jspb$Map_Map.prototype.entries);
    module$contents$jspb$Map_Map.prototype.keys = function() {
      var a2 = [], b2 = this.stringKeys_();
      b2.sort();
      for (var c = 0; c < b2.length; c++) a2.push(this.map_[b2[c]].key);
      return new module$contents$jspb$Map_ArrayIteratorIterable_(a2);
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "keys", module$contents$jspb$Map_Map.prototype.keys);
    module$contents$jspb$Map_Map.prototype.values = function() {
      var a2 = [], b2 = this.stringKeys_();
      b2.sort();
      for (var c = 0; c < b2.length; c++) a2.push(this.wrapEntry_(this.map_[b2[c]]));
      return new module$contents$jspb$Map_ArrayIteratorIterable_(a2);
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "values", module$contents$jspb$Map_Map.prototype.values);
    module$contents$jspb$Map_Map.prototype.forEach = function(a2, b2) {
      var c = this.stringKeys_();
      c.sort();
      for (var d = 0; d < c.length; d++) {
        var e = this.map_[c[d]];
        a2.call(b2, this.wrapEntry_(e), e.key, this);
      }
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "forEach", module$contents$jspb$Map_Map.prototype.forEach);
    module$contents$jspb$Map_Map.prototype.set = function(a2, b2) {
      var c = new module$contents$jspb$Map_Entry_(a2);
      this.valueCtor_ ? (c.valueWrapper = b2, c.value = b2.toArray()) : c.value = b2;
      this.map_[a2.toString()] = c;
      this.arrClean = false;
      return this;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "set", module$contents$jspb$Map_Map.prototype.set);
    module$contents$jspb$Map_Map.prototype.wrapEntry_ = function(a2) {
      return this.valueCtor_ ? (a2.valueWrapper || (a2.valueWrapper = new this.valueCtor_(a2.value)), a2.valueWrapper) : a2.value;
    };
    module$contents$jspb$Map_Map.prototype.get = function(a2) {
      if (a2 = this.map_[a2.toString()]) return this.wrapEntry_(a2);
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "get", module$contents$jspb$Map_Map.prototype.get);
    module$contents$jspb$Map_Map.prototype.has = function(a2) {
      return a2.toString() in this.map_;
    };
    goog.exportProperty(module$contents$jspb$Map_Map.prototype, "has", module$contents$jspb$Map_Map.prototype.has);
    module$contents$jspb$Map_Map.deserializeBinary = function(a2, b2, c, d, e, f, g) {
      for (; b2.nextField() && !b2.isEndGroup(); ) {
        var h = b2.getFieldNumber();
        1 == h ? f = c.call(b2) : 2 == h && (a2.valueCtor_ ? (module$contents$jspb$asserts_assert(e), g || (g = new a2.valueCtor_()), d.call(b2, g, e)) : g = d.call(b2));
      }
      module$contents$jspb$asserts_assert(void 0 != f);
      module$contents$jspb$asserts_assert(void 0 != g);
      a2.set(f, g);
    };
    goog.exportSymbol("module$contents$jspb$Map_Map.deserializeBinary", module$contents$jspb$Map_Map.deserializeBinary);
    module$contents$jspb$Map_Map.prototype.stringKeys_ = function() {
      var a2 = this.map_, b2 = [], c;
      for (c in a2) Object.prototype.hasOwnProperty.call(a2, c) && b2.push(c);
      return b2;
    };
    jspb.Map = module$contents$jspb$Map_Map;
    goog.async = {};
    function module$contents$goog$async$throwException_throwException(a2) {
      goog.global.setTimeout(() => {
        throw a2;
      }, 0);
    }
    goog.async.throwException = module$contents$goog$async$throwException_throwException;
    goog.crypt = {};
    goog.crypt.ASYNC_THROW_ON_UNICODE_TO_BYTE = goog.DEBUG;
    goog.crypt.TEST_ONLY = {};
    goog.crypt.TEST_ONLY.throwException = module$contents$goog$async$throwException_throwException;
    goog.crypt.TEST_ONLY.alwaysThrowSynchronously = goog.DEBUG;
    goog.crypt.binaryStringToByteArray = function(a2) {
      return goog.crypt.stringToByteArray(a2, true);
    };
    goog.crypt.stringToByteArray = function(a2, b2) {
      for (var c = [], d = 0, e = 0; e < a2.length; e++) {
        var f = a2.charCodeAt(e);
        if (255 < f) {
          var g = Error("go/unicode-to-byte-error");
          if (goog.crypt.TEST_ONLY.alwaysThrowSynchronously || b2) throw g;
          goog.crypt.ASYNC_THROW_ON_UNICODE_TO_BYTE && goog.crypt.TEST_ONLY.throwException(g);
          c[d++] = f & 255;
          f >>= 8;
        }
        c[d++] = f;
      }
      return c;
    };
    goog.crypt.byteArrayToString = function(a2) {
      return goog.crypt.byteArrayToBinaryString(a2);
    };
    goog.crypt.byteArrayToBinaryString = function(a2) {
      if (8192 >= a2.length) return String.fromCharCode.apply(null, a2);
      for (var b2 = "", c = 0; c < a2.length; c += 8192) {
        var d = Array.prototype.slice.call(a2, c, c + 8192);
        b2 += String.fromCharCode.apply(null, d);
      }
      return b2;
    };
    goog.crypt.byteArrayToHex = function(a2, b2) {
      return Array.prototype.map.call(a2, function(c) {
        c = c.toString(16);
        return 1 < c.length ? c : "0" + c;
      }).join(b2 || "");
    };
    goog.crypt.hexToByteArray = function(a2) {
      goog.asserts.assert(0 == a2.length % 2, "Key string length must be multiple of 2");
      for (var b2 = [], c = 0; c < a2.length; c += 2) b2.push(parseInt(a2.substring(c, c + 2), 16));
      return b2;
    };
    goog.crypt.stringToUtf8ByteArray = function(a2) {
      return goog.crypt.textToByteArray(a2);
    };
    goog.crypt.textToByteArray = function(a2) {
      for (var b2 = [], c = 0, d = 0; d < a2.length; d++) {
        var e = a2.charCodeAt(d);
        128 > e ? b2[c++] = e : (2048 > e ? b2[c++] = e >> 6 | 192 : (55296 == (e & 64512) && d + 1 < a2.length && 56320 == (a2.charCodeAt(d + 1) & 64512) ? (e = 65536 + ((e & 1023) << 10) + (a2.charCodeAt(++d) & 1023), b2[c++] = e >> 18 | 240, b2[c++] = e >> 12 & 63 | 128) : b2[c++] = e >> 12 | 224, b2[c++] = e >> 6 & 63 | 128), b2[c++] = e & 63 | 128);
      }
      return b2;
    };
    goog.crypt.utf8ByteArrayToString = function(a2) {
      return goog.crypt.byteArrayToText(a2);
    };
    goog.crypt.byteArrayToText = function(a2) {
      for (var b2 = [], c = 0, d = 0; c < a2.length; ) {
        var e = a2[c++];
        if (128 > e) b2[d++] = String.fromCharCode(e);
        else if (191 < e && 224 > e) {
          var f = a2[c++];
          b2[d++] = String.fromCharCode((e & 31) << 6 | f & 63);
        } else if (239 < e && 365 > e) {
          f = a2[c++];
          var g = a2[c++], h = a2[c++];
          e = ((e & 7) << 18 | (f & 63) << 12 | (g & 63) << 6 | h & 63) - 65536;
          b2[d++] = String.fromCharCode(55296 + (e >> 10));
          b2[d++] = String.fromCharCode(56320 + (e & 1023));
        } else f = a2[c++], g = a2[c++], b2[d++] = String.fromCharCode((e & 15) << 12 | (f & 63) << 6 | g & 63);
      }
      return b2.join("");
    };
    goog.crypt.xorByteArray = function(a2, b2) {
      goog.asserts.assert(a2.length == b2.length, "XOR array lengths must match");
      for (var c = [], d = 0; d < a2.length; d++) c.push(a2[d] ^ b2[d]);
      return c;
    };
    goog.string = {};
    goog.string.internal = {};
    goog.string.internal.startsWith = function(a2, b2) {
      return 0 == a2.lastIndexOf(b2, 0);
    };
    goog.string.internal.endsWith = function(a2, b2) {
      const c = a2.length - b2.length;
      return 0 <= c && a2.indexOf(b2, c) == c;
    };
    goog.string.internal.caseInsensitiveStartsWith = function(a2, b2) {
      return 0 == goog.string.internal.caseInsensitiveCompare(b2, a2.slice(0, b2.length));
    };
    goog.string.internal.caseInsensitiveEndsWith = function(a2, b2) {
      return 0 == goog.string.internal.caseInsensitiveCompare(b2, a2.slice(a2.length - b2.length));
    };
    goog.string.internal.caseInsensitiveEquals = function(a2, b2) {
      return a2.toLowerCase() == b2.toLowerCase();
    };
    goog.string.internal.isEmptyOrWhitespace = function(a2) {
      return /^[\s\xa0]*$/.test(a2);
    };
    goog.string.internal.trim = goog.TRUSTED_SITE && String.prototype.trim ? function(a2) {
      return a2.trim();
    } : function(a2) {
      return /^[\s\xa0]*([\s\S]*?)[\s\xa0]*$/.exec(a2)[1];
    };
    goog.string.internal.caseInsensitiveCompare = function(a2, b2) {
      a2 = String(a2).toLowerCase();
      b2 = String(b2).toLowerCase();
      return a2 < b2 ? -1 : a2 == b2 ? 0 : 1;
    };
    goog.string.internal.newLineToBr = function(a2, b2) {
      return a2.replace(/(\r\n|\r|\n)/g, b2 ? "<br />" : "<br>");
    };
    goog.string.internal.htmlEscape = function(a2, b2) {
      if (b2) a2 = a2.replace(goog.string.internal.AMP_RE_, "&amp;").replace(goog.string.internal.LT_RE_, "&lt;").replace(goog.string.internal.GT_RE_, "&gt;").replace(goog.string.internal.QUOT_RE_, "&quot;").replace(goog.string.internal.SINGLE_QUOTE_RE_, "&#39;").replace(goog.string.internal.NULL_RE_, "&#0;");
      else {
        if (!goog.string.internal.ALL_RE_.test(a2)) return a2;
        -1 != a2.indexOf("&") && (a2 = a2.replace(goog.string.internal.AMP_RE_, "&amp;"));
        -1 != a2.indexOf("<") && (a2 = a2.replace(
          goog.string.internal.LT_RE_,
          "&lt;"
        ));
        -1 != a2.indexOf(">") && (a2 = a2.replace(goog.string.internal.GT_RE_, "&gt;"));
        -1 != a2.indexOf('"') && (a2 = a2.replace(goog.string.internal.QUOT_RE_, "&quot;"));
        -1 != a2.indexOf("'") && (a2 = a2.replace(goog.string.internal.SINGLE_QUOTE_RE_, "&#39;"));
        -1 != a2.indexOf("\0") && (a2 = a2.replace(goog.string.internal.NULL_RE_, "&#0;"));
      }
      return a2;
    };
    goog.string.internal.AMP_RE_ = /&/g;
    goog.string.internal.LT_RE_ = /</g;
    goog.string.internal.GT_RE_ = />/g;
    goog.string.internal.QUOT_RE_ = /"/g;
    goog.string.internal.SINGLE_QUOTE_RE_ = /'/g;
    goog.string.internal.NULL_RE_ = /\x00/g;
    goog.string.internal.ALL_RE_ = /[\x00&<>"']/;
    goog.string.internal.whitespaceEscape = function(a2, b2) {
      return goog.string.internal.newLineToBr(a2.replace(/  /g, " &#160;"), b2);
    };
    goog.string.internal.contains = function(a2, b2) {
      return -1 != a2.indexOf(b2);
    };
    goog.string.internal.caseInsensitiveContains = function(a2, b2) {
      return goog.string.internal.contains(a2.toLowerCase(), b2.toLowerCase());
    };
    goog.string.internal.compareVersions = function(a2, b2) {
      var c = 0;
      a2 = goog.string.internal.trim(String(a2)).split(".");
      b2 = goog.string.internal.trim(String(b2)).split(".");
      const d = Math.max(a2.length, b2.length);
      for (let g = 0; 0 == c && g < d; g++) {
        var e = a2[g] || "", f = b2[g] || "";
        do {
          e = /(\d*)(\D*)(.*)/.exec(e) || ["", "", "", ""];
          f = /(\d*)(\D*)(.*)/.exec(f) || ["", "", "", ""];
          if (0 == e[0].length && 0 == f[0].length) break;
          c = 0 == e[1].length ? 0 : parseInt(e[1], 10);
          const h = 0 == f[1].length ? 0 : parseInt(f[1], 10);
          c = goog.string.internal.compareElements_(c, h) || goog.string.internal.compareElements_(0 == e[2].length, 0 == f[2].length) || goog.string.internal.compareElements_(e[2], f[2]);
          e = e[3];
          f = f[3];
        } while (0 == c);
      }
      return c;
    };
    goog.string.internal.compareElements_ = function(a2, b2) {
      return a2 < b2 ? -1 : a2 > b2 ? 1 : 0;
    };
    goog.flags = {};
    goog.flags.USE_USER_AGENT_CLIENT_HINTS = false;
    goog.flags.ASYNC_THROW_ON_UNICODE_TO_BYTE = false;
    goog.labs = {};
    goog.labs.userAgent = {};
    var module$contents$goog$labs$userAgent_USE_CLIENT_HINTS_OVERRIDE = "";
    var module$contents$goog$labs$userAgent_USE_CLIENT_HINTS = false;
    var module$contents$goog$labs$userAgent_forceClientHintsInTests = false;
    goog.labs.userAgent.setUseClientHintsForTesting = (a2) => {
      module$contents$goog$labs$userAgent_forceClientHintsInTests = a2;
    };
    var module$contents$goog$labs$userAgent_useClientHintsRuntimeOverride = module$contents$goog$labs$userAgent_USE_CLIENT_HINTS_OVERRIDE ? !!goog.getObjectByName(module$contents$goog$labs$userAgent_USE_CLIENT_HINTS_OVERRIDE) : false;
    goog.labs.userAgent.useClientHints = () => goog.flags.USE_USER_AGENT_CLIENT_HINTS || module$contents$goog$labs$userAgent_USE_CLIENT_HINTS || module$contents$goog$labs$userAgent_useClientHintsRuntimeOverride || module$contents$goog$labs$userAgent_forceClientHintsInTests;
    goog.labs.userAgent.util = {};
    var module$contents$goog$labs$userAgent$util_ASSUME_CLIENT_HINTS_SUPPORT = false;
    function module$contents$goog$labs$userAgent$util_getNativeUserAgentString() {
      var a2 = module$contents$goog$labs$userAgent$util_getNavigator();
      return a2 && (a2 = a2.userAgent) ? a2 : "";
    }
    function module$contents$goog$labs$userAgent$util_getNativeUserAgentData() {
      const a2 = module$contents$goog$labs$userAgent$util_getNavigator();
      return a2 ? a2.userAgentData || null : null;
    }
    function module$contents$goog$labs$userAgent$util_getNavigator() {
      return goog.global.navigator;
    }
    var module$contents$goog$labs$userAgent$util_userAgentInternal = null;
    var module$contents$goog$labs$userAgent$util_userAgentDataInternal = module$contents$goog$labs$userAgent$util_getNativeUserAgentData();
    function module$contents$goog$labs$userAgent$util_setUserAgent(a2) {
      module$contents$goog$labs$userAgent$util_userAgentInternal = "string" === typeof a2 ? a2 : module$contents$goog$labs$userAgent$util_getNativeUserAgentString();
    }
    function module$contents$goog$labs$userAgent$util_getUserAgent() {
      return null == module$contents$goog$labs$userAgent$util_userAgentInternal ? module$contents$goog$labs$userAgent$util_getNativeUserAgentString() : module$contents$goog$labs$userAgent$util_userAgentInternal;
    }
    function module$contents$goog$labs$userAgent$util_setUserAgentData(a2) {
      module$contents$goog$labs$userAgent$util_userAgentDataInternal = a2;
    }
    function module$contents$goog$labs$userAgent$util_resetUserAgentData() {
      module$contents$goog$labs$userAgent$util_userAgentDataInternal = module$contents$goog$labs$userAgent$util_getNativeUserAgentData();
    }
    function module$contents$goog$labs$userAgent$util_getUserAgentData() {
      return module$contents$goog$labs$userAgent$util_userAgentDataInternal;
    }
    function module$contents$goog$labs$userAgent$util_matchUserAgentDataBrand(a2) {
      if (!(0, goog.labs.userAgent.useClientHints)()) return false;
      const b2 = module$contents$goog$labs$userAgent$util_getUserAgentData();
      return b2 ? b2.brands.some(({ brand: c }) => c && (0, goog.string.internal.contains)(c, a2)) : false;
    }
    function module$contents$goog$labs$userAgent$util_matchUserAgent(a2) {
      const b2 = module$contents$goog$labs$userAgent$util_getUserAgent();
      return (0, goog.string.internal.contains)(b2, a2);
    }
    function module$contents$goog$labs$userAgent$util_matchUserAgentIgnoreCase(a2) {
      const b2 = module$contents$goog$labs$userAgent$util_getUserAgent();
      return (0, goog.string.internal.caseInsensitiveContains)(b2, a2);
    }
    function module$contents$goog$labs$userAgent$util_extractVersionTuples(a2) {
      const b2 = RegExp("([A-Z][\\w ]+)/([^\\s]+)\\s*(?:\\((.*?)\\))?", "g"), c = [];
      let d;
      for (; d = b2.exec(a2); ) c.push([d[1], d[2], d[3] || void 0]);
      return c;
    }
    goog.labs.userAgent.util.ASSUME_CLIENT_HINTS_SUPPORT = module$contents$goog$labs$userAgent$util_ASSUME_CLIENT_HINTS_SUPPORT;
    goog.labs.userAgent.util.extractVersionTuples = module$contents$goog$labs$userAgent$util_extractVersionTuples;
    goog.labs.userAgent.util.getNativeUserAgentString = module$contents$goog$labs$userAgent$util_getNativeUserAgentString;
    goog.labs.userAgent.util.getUserAgent = module$contents$goog$labs$userAgent$util_getUserAgent;
    goog.labs.userAgent.util.getUserAgentData = module$contents$goog$labs$userAgent$util_getUserAgentData;
    goog.labs.userAgent.util.matchUserAgent = module$contents$goog$labs$userAgent$util_matchUserAgent;
    goog.labs.userAgent.util.matchUserAgentDataBrand = module$contents$goog$labs$userAgent$util_matchUserAgentDataBrand;
    goog.labs.userAgent.util.matchUserAgentIgnoreCase = module$contents$goog$labs$userAgent$util_matchUserAgentIgnoreCase;
    goog.labs.userAgent.util.resetUserAgentData = module$contents$goog$labs$userAgent$util_resetUserAgentData;
    goog.labs.userAgent.util.setUserAgent = module$contents$goog$labs$userAgent$util_setUserAgent;
    goog.labs.userAgent.util.setUserAgentData = module$contents$goog$labs$userAgent$util_setUserAgentData;
    var module$exports$goog$labs$userAgent$highEntropy$highEntropyValue = { AsyncValue: class {
      getIfLoaded() {
      }
      load() {
      }
    }, HighEntropyValue: class {
      constructor(a2) {
        this.key_ = a2;
        this.promise_ = this.value_ = void 0;
        this.pending_ = false;
      }
      getIfLoaded() {
        if (module$contents$goog$labs$userAgent$util_getUserAgentData()) return this.value_;
      }
      async load() {
        const a2 = module$contents$goog$labs$userAgent$util_getUserAgentData();
        if (a2) return this.promise_ || (this.pending_ = true, this.promise_ = (async () => {
          try {
            return this.value_ = (await a2.getHighEntropyValues([this.key_]))[this.key_];
          } finally {
            this.pending_ = false;
          }
        })()), await this.promise_;
      }
      resetForTesting() {
        if (this.pending_) throw Error("Unsafe call to resetForTesting");
        this.value_ = this.promise_ = void 0;
        this.pending_ = false;
      }
    }, Version: class {
      constructor(a2) {
        this.versionString_ = a2;
      }
      toVersionStringForLogging() {
        return this.versionString_;
      }
      isAtLeast(a2) {
        return 0 <= (0, goog.string.internal.compareVersions)(this.versionString_, a2);
      }
    } };
    var module$exports$goog$labs$userAgent$highEntropy$highEntropyData = {};
    module$exports$goog$labs$userAgent$highEntropy$highEntropyData.fullVersionList = new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.HighEntropyValue("fullVersionList");
    module$exports$goog$labs$userAgent$highEntropy$highEntropyData.platformVersion = new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.HighEntropyValue("platformVersion");
    goog.labs.userAgent.browser = {};
    var module$contents$goog$labs$userAgent$browser_Brand = { ANDROID_BROWSER: "Android Browser", CHROMIUM: "Chromium", EDGE: "Microsoft Edge", FIREFOX: "Firefox", IE: "Internet Explorer", OPERA: "Opera", SAFARI: "Safari", SILK: "Silk" };
    goog.labs.userAgent.browser.Brand = module$contents$goog$labs$userAgent$browser_Brand;
    function module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand(a2 = false) {
      if (module$contents$goog$labs$userAgent$util_ASSUME_CLIENT_HINTS_SUPPORT) return true;
      if (!a2 && !(0, goog.labs.userAgent.useClientHints)()) return false;
      a2 = module$contents$goog$labs$userAgent$util_getUserAgentData();
      return !!a2 && 0 < a2.brands.length;
    }
    function module$contents$goog$labs$userAgent$browser_hasFullVersionList() {
      return module$contents$goog$labs$userAgent$browser_isAtLeast(module$contents$goog$labs$userAgent$browser_Brand.CHROMIUM, 98);
    }
    function module$contents$goog$labs$userAgent$browser_matchOpera() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? false : module$contents$goog$labs$userAgent$util_matchUserAgent("Opera");
    }
    function module$contents$goog$labs$userAgent$browser_matchIE() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? false : module$contents$goog$labs$userAgent$util_matchUserAgent("Trident") || module$contents$goog$labs$userAgent$util_matchUserAgent("MSIE");
    }
    function module$contents$goog$labs$userAgent$browser_matchEdgeHtml() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? false : module$contents$goog$labs$userAgent$util_matchUserAgent("Edge");
    }
    function module$contents$goog$labs$userAgent$browser_matchEdgeChromium() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? module$contents$goog$labs$userAgent$util_matchUserAgentDataBrand(module$contents$goog$labs$userAgent$browser_Brand.EDGE) : module$contents$goog$labs$userAgent$util_matchUserAgent("Edg/");
    }
    function module$contents$goog$labs$userAgent$browser_matchOperaChromium() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? module$contents$goog$labs$userAgent$util_matchUserAgentDataBrand(module$contents$goog$labs$userAgent$browser_Brand.OPERA) : module$contents$goog$labs$userAgent$util_matchUserAgent("OPR");
    }
    function module$contents$goog$labs$userAgent$browser_matchFirefox() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Firefox") || module$contents$goog$labs$userAgent$util_matchUserAgent("FxiOS");
    }
    function module$contents$goog$labs$userAgent$browser_matchSafari() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Safari") && !(module$contents$goog$labs$userAgent$browser_matchChrome() || module$contents$goog$labs$userAgent$browser_matchCoast() || module$contents$goog$labs$userAgent$browser_matchOpera() || module$contents$goog$labs$userAgent$browser_matchEdgeHtml() || module$contents$goog$labs$userAgent$browser_matchEdgeChromium() || module$contents$goog$labs$userAgent$browser_matchOperaChromium() || module$contents$goog$labs$userAgent$browser_matchFirefox() || module$contents$goog$labs$userAgent$browser_isSilk() || module$contents$goog$labs$userAgent$util_matchUserAgent("Android"));
    }
    function module$contents$goog$labs$userAgent$browser_matchCoast() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? false : module$contents$goog$labs$userAgent$util_matchUserAgent("Coast");
    }
    function module$contents$goog$labs$userAgent$browser_matchIosWebview() {
      return (module$contents$goog$labs$userAgent$util_matchUserAgent("iPad") || module$contents$goog$labs$userAgent$util_matchUserAgent("iPhone")) && !module$contents$goog$labs$userAgent$browser_matchSafari() && !module$contents$goog$labs$userAgent$browser_matchChrome() && !module$contents$goog$labs$userAgent$browser_matchCoast() && !module$contents$goog$labs$userAgent$browser_matchFirefox() && module$contents$goog$labs$userAgent$util_matchUserAgent("AppleWebKit");
    }
    function module$contents$goog$labs$userAgent$browser_matchChrome() {
      return module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() ? module$contents$goog$labs$userAgent$util_matchUserAgentDataBrand(module$contents$goog$labs$userAgent$browser_Brand.CHROMIUM) : (module$contents$goog$labs$userAgent$util_matchUserAgent("Chrome") || module$contents$goog$labs$userAgent$util_matchUserAgent("CriOS")) && !module$contents$goog$labs$userAgent$browser_matchEdgeHtml() || module$contents$goog$labs$userAgent$browser_isSilk();
    }
    function module$contents$goog$labs$userAgent$browser_matchAndroidBrowser() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Android") && !(module$contents$goog$labs$userAgent$browser_matchChrome() || module$contents$goog$labs$userAgent$browser_matchFirefox() || module$contents$goog$labs$userAgent$browser_matchOpera() || module$contents$goog$labs$userAgent$browser_isSilk());
    }
    var module$contents$goog$labs$userAgent$browser_isOpera = module$contents$goog$labs$userAgent$browser_matchOpera;
    goog.labs.userAgent.browser.isOpera = module$contents$goog$labs$userAgent$browser_matchOpera;
    var module$contents$goog$labs$userAgent$browser_isIE = module$contents$goog$labs$userAgent$browser_matchIE;
    goog.labs.userAgent.browser.isIE = module$contents$goog$labs$userAgent$browser_matchIE;
    var module$contents$goog$labs$userAgent$browser_isEdge = module$contents$goog$labs$userAgent$browser_matchEdgeHtml;
    goog.labs.userAgent.browser.isEdge = module$contents$goog$labs$userAgent$browser_matchEdgeHtml;
    var module$contents$goog$labs$userAgent$browser_isEdgeChromium = module$contents$goog$labs$userAgent$browser_matchEdgeChromium;
    goog.labs.userAgent.browser.isEdgeChromium = module$contents$goog$labs$userAgent$browser_matchEdgeChromium;
    var module$contents$goog$labs$userAgent$browser_isOperaChromium = module$contents$goog$labs$userAgent$browser_matchOperaChromium;
    goog.labs.userAgent.browser.isOperaChromium = module$contents$goog$labs$userAgent$browser_matchOperaChromium;
    var module$contents$goog$labs$userAgent$browser_isFirefox = module$contents$goog$labs$userAgent$browser_matchFirefox;
    goog.labs.userAgent.browser.isFirefox = module$contents$goog$labs$userAgent$browser_matchFirefox;
    var module$contents$goog$labs$userAgent$browser_isSafari = module$contents$goog$labs$userAgent$browser_matchSafari;
    goog.labs.userAgent.browser.isSafari = module$contents$goog$labs$userAgent$browser_matchSafari;
    var module$contents$goog$labs$userAgent$browser_isCoast = module$contents$goog$labs$userAgent$browser_matchCoast;
    goog.labs.userAgent.browser.isCoast = module$contents$goog$labs$userAgent$browser_matchCoast;
    var module$contents$goog$labs$userAgent$browser_isIosWebview = module$contents$goog$labs$userAgent$browser_matchIosWebview;
    goog.labs.userAgent.browser.isIosWebview = module$contents$goog$labs$userAgent$browser_matchIosWebview;
    var module$contents$goog$labs$userAgent$browser_isChrome = module$contents$goog$labs$userAgent$browser_matchChrome;
    goog.labs.userAgent.browser.isChrome = module$contents$goog$labs$userAgent$browser_matchChrome;
    var module$contents$goog$labs$userAgent$browser_isAndroidBrowser = module$contents$goog$labs$userAgent$browser_matchAndroidBrowser;
    goog.labs.userAgent.browser.isAndroidBrowser = module$contents$goog$labs$userAgent$browser_matchAndroidBrowser;
    function module$contents$goog$labs$userAgent$browser_isSilk() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Silk");
    }
    goog.labs.userAgent.browser.isSilk = module$contents$goog$labs$userAgent$browser_isSilk;
    function module$contents$goog$labs$userAgent$browser_createVersionMap(a2) {
      const b2 = {};
      a2.forEach((c) => {
        b2[c[0]] = c[1];
      });
      return (c) => b2[c.find((d) => d in b2)] || "";
    }
    function module$contents$goog$labs$userAgent$browser_getVersion() {
      var a2 = module$contents$goog$labs$userAgent$util_getUserAgent();
      if (module$contents$goog$labs$userAgent$browser_matchIE()) return module$contents$goog$labs$userAgent$browser_getIEVersion(a2);
      a2 = module$contents$goog$labs$userAgent$util_extractVersionTuples(a2);
      const b2 = module$contents$goog$labs$userAgent$browser_createVersionMap(a2);
      return module$contents$goog$labs$userAgent$browser_matchOpera() ? b2(["Version", "Opera"]) : module$contents$goog$labs$userAgent$browser_matchEdgeHtml() ? b2(["Edge"]) : module$contents$goog$labs$userAgent$browser_matchEdgeChromium() ? b2(["Edg"]) : module$contents$goog$labs$userAgent$browser_isSilk() ? b2(["Silk"]) : module$contents$goog$labs$userAgent$browser_matchChrome() ? b2(["Chrome", "CriOS", "HeadlessChrome"]) : (a2 = a2[2]) && a2[1] || "";
    }
    goog.labs.userAgent.browser.getVersion = module$contents$goog$labs$userAgent$browser_getVersion;
    function module$contents$goog$labs$userAgent$browser_isVersionOrHigher(a2) {
      return 0 <= (0, goog.string.internal.compareVersions)(module$contents$goog$labs$userAgent$browser_getVersion(), a2);
    }
    goog.labs.userAgent.browser.isVersionOrHigher = module$contents$goog$labs$userAgent$browser_isVersionOrHigher;
    function module$contents$goog$labs$userAgent$browser_getIEVersion(a2) {
      var b2 = /rv: *([\d\.]*)/.exec(a2);
      if (b2 && b2[1]) return b2[1];
      b2 = "";
      const c = /MSIE +([\d\.]+)/.exec(a2);
      if (c && c[1]) if (a2 = /Trident\/(\d.\d)/.exec(a2), "7.0" == c[1]) if (a2 && a2[1]) switch (a2[1]) {
        case "4.0":
          b2 = "8.0";
          break;
        case "5.0":
          b2 = "9.0";
          break;
        case "6.0":
          b2 = "10.0";
          break;
        case "7.0":
          b2 = "11.0";
      }
      else b2 = "7.0";
      else b2 = c[1];
      return b2;
    }
    function module$contents$goog$labs$userAgent$browser_getFullVersionFromUserAgentString(a2) {
      var b2 = module$contents$goog$labs$userAgent$util_getUserAgent();
      if (a2 === module$contents$goog$labs$userAgent$browser_Brand.IE) return module$contents$goog$labs$userAgent$browser_matchIE() ? module$contents$goog$labs$userAgent$browser_getIEVersion(b2) : "";
      b2 = module$contents$goog$labs$userAgent$util_extractVersionTuples(b2);
      const c = module$contents$goog$labs$userAgent$browser_createVersionMap(b2);
      switch (a2) {
        case module$contents$goog$labs$userAgent$browser_Brand.OPERA:
          if (module$contents$goog$labs$userAgent$browser_matchOpera()) return c([
            "Version",
            "Opera"
          ]);
          if (module$contents$goog$labs$userAgent$browser_matchOperaChromium()) return c(["OPR"]);
          break;
        case module$contents$goog$labs$userAgent$browser_Brand.EDGE:
          if (module$contents$goog$labs$userAgent$browser_matchEdgeHtml()) return c(["Edge"]);
          if (module$contents$goog$labs$userAgent$browser_matchEdgeChromium()) return c(["Edg"]);
          break;
        case module$contents$goog$labs$userAgent$browser_Brand.CHROMIUM:
          if (module$contents$goog$labs$userAgent$browser_matchChrome()) return c(["Chrome", "CriOS", "HeadlessChrome"]);
      }
      return a2 === module$contents$goog$labs$userAgent$browser_Brand.FIREFOX && module$contents$goog$labs$userAgent$browser_matchFirefox() || a2 === module$contents$goog$labs$userAgent$browser_Brand.SAFARI && module$contents$goog$labs$userAgent$browser_matchSafari() || a2 === module$contents$goog$labs$userAgent$browser_Brand.ANDROID_BROWSER && module$contents$goog$labs$userAgent$browser_matchAndroidBrowser() || a2 === module$contents$goog$labs$userAgent$browser_Brand.SILK && module$contents$goog$labs$userAgent$browser_isSilk() ? (a2 = b2[2]) && a2[1] || "" : "";
    }
    function module$contents$goog$labs$userAgent$browser_versionOf_(a2) {
      if (module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand() && a2 !== module$contents$goog$labs$userAgent$browser_Brand.SILK) {
        var b2 = module$contents$goog$labs$userAgent$util_getUserAgentData().brands.find(({ brand: c }) => c === a2);
        if (!b2 || !b2.version) return NaN;
        b2 = b2.version.split(".");
      } else {
        b2 = module$contents$goog$labs$userAgent$browser_getFullVersionFromUserAgentString(a2);
        if ("" === b2) return NaN;
        b2 = b2.split(".");
      }
      return 0 === b2.length ? NaN : Number(b2[0]);
    }
    function module$contents$goog$labs$userAgent$browser_isAtLeast(a2, b2) {
      (0, goog.asserts.assert)(Math.floor(b2) === b2, "Major version must be an integer");
      return module$contents$goog$labs$userAgent$browser_versionOf_(a2) >= b2;
    }
    goog.labs.userAgent.browser.isAtLeast = module$contents$goog$labs$userAgent$browser_isAtLeast;
    function module$contents$goog$labs$userAgent$browser_isAtMost(a2, b2) {
      (0, goog.asserts.assert)(Math.floor(b2) === b2, "Major version must be an integer");
      return module$contents$goog$labs$userAgent$browser_versionOf_(a2) <= b2;
    }
    goog.labs.userAgent.browser.isAtMost = module$contents$goog$labs$userAgent$browser_isAtMost;
    var module$contents$goog$labs$userAgent$browser_HighEntropyBrandVersion = class {
      constructor(a2, b2, c) {
        this.brand_ = a2;
        this.version_ = new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(c);
        this.useUach_ = b2;
      }
      getIfLoaded() {
        if (this.useUach_) {
          var a2 = module$exports$goog$labs$userAgent$highEntropy$highEntropyData.fullVersionList.getIfLoaded();
          if (void 0 !== a2) return a2 = a2.find(({ brand: b2 }) => this.brand_ === b2), (0, goog.asserts.assertExists)(a2), new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(a2.version);
        }
        if (module$contents$goog$labs$userAgent$browser_preUachHasLoaded) return this.version_;
      }
      async load() {
        if (this.useUach_) {
          var a2 = await module$exports$goog$labs$userAgent$highEntropy$highEntropyData.fullVersionList.load();
          if (void 0 !== a2) return a2 = a2.find(({ brand: b2 }) => this.brand_ === b2), (0, goog.asserts.assertExists)(a2), new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(a2.version);
        } else await 0;
        module$contents$goog$labs$userAgent$browser_preUachHasLoaded = true;
        return this.version_;
      }
    };
    var module$contents$goog$labs$userAgent$browser_preUachHasLoaded = false;
    async function module$contents$goog$labs$userAgent$browser_loadFullVersions() {
      module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand(true) && await module$exports$goog$labs$userAgent$highEntropy$highEntropyData.fullVersionList.load();
      module$contents$goog$labs$userAgent$browser_preUachHasLoaded = true;
    }
    goog.labs.userAgent.browser.loadFullVersions = module$contents$goog$labs$userAgent$browser_loadFullVersions;
    goog.labs.userAgent.browser.resetForTesting = () => {
      module$contents$goog$labs$userAgent$browser_preUachHasLoaded = false;
      module$exports$goog$labs$userAgent$highEntropy$highEntropyData.fullVersionList.resetForTesting();
    };
    function module$contents$goog$labs$userAgent$browser_fullVersionOf(a2) {
      let b2 = "";
      module$contents$goog$labs$userAgent$browser_hasFullVersionList() || (b2 = module$contents$goog$labs$userAgent$browser_getFullVersionFromUserAgentString(a2));
      const c = a2 !== module$contents$goog$labs$userAgent$browser_Brand.SILK && module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand(true);
      if (c) {
        if (!module$contents$goog$labs$userAgent$util_getUserAgentData().brands.find(({ brand: d }) => d === a2)) return;
      } else if ("" === b2) return;
      return new module$contents$goog$labs$userAgent$browser_HighEntropyBrandVersion(
        a2,
        c,
        b2
      );
    }
    goog.labs.userAgent.browser.fullVersionOf = module$contents$goog$labs$userAgent$browser_fullVersionOf;
    function module$contents$goog$labs$userAgent$browser_getVersionStringForLogging(a2) {
      if (module$contents$goog$labs$userAgent$browser_useUserAgentDataBrand(true)) {
        var b2 = module$contents$goog$labs$userAgent$browser_fullVersionOf(a2);
        if (b2) {
          if (b2 = b2.getIfLoaded()) return b2.toVersionStringForLogging();
          b2 = module$contents$goog$labs$userAgent$util_getUserAgentData().brands.find(({ brand: c }) => c === a2);
          (0, goog.asserts.assertExists)(b2);
          return b2.version;
        }
        return "";
      }
      return module$contents$goog$labs$userAgent$browser_getFullVersionFromUserAgentString(a2);
    }
    goog.labs.userAgent.browser.getVersionStringForLogging = module$contents$goog$labs$userAgent$browser_getVersionStringForLogging;
    goog.labs.userAgent.engine = {};
    function module$contents$goog$labs$userAgent$engine_isPresto() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Presto");
    }
    function module$contents$goog$labs$userAgent$engine_isTrident() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Trident") || module$contents$goog$labs$userAgent$util_matchUserAgent("MSIE");
    }
    function module$contents$goog$labs$userAgent$engine_isEdge() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Edge");
    }
    function module$contents$goog$labs$userAgent$engine_isWebKit() {
      return module$contents$goog$labs$userAgent$util_matchUserAgentIgnoreCase("WebKit") && !module$contents$goog$labs$userAgent$engine_isEdge();
    }
    function module$contents$goog$labs$userAgent$engine_isGecko() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("Gecko") && !module$contents$goog$labs$userAgent$engine_isWebKit() && !module$contents$goog$labs$userAgent$engine_isTrident() && !module$contents$goog$labs$userAgent$engine_isEdge();
    }
    function module$contents$goog$labs$userAgent$engine_getVersion() {
      var a2 = module$contents$goog$labs$userAgent$util_getUserAgent();
      if (a2) {
        a2 = module$contents$goog$labs$userAgent$util_extractVersionTuples(a2);
        const c = module$contents$goog$labs$userAgent$engine_getEngineTuple(a2);
        if (c) return "Gecko" == c[0] ? module$contents$goog$labs$userAgent$engine_getVersionForKey(a2, "Firefox") : c[1];
        a2 = a2[0];
        var b2;
        if (a2 && (b2 = a2[2]) && (b2 = /Trident\/([^\s;]+)/.exec(b2))) return b2[1];
      }
      return "";
    }
    function module$contents$goog$labs$userAgent$engine_getEngineTuple(a2) {
      if (!module$contents$goog$labs$userAgent$engine_isEdge()) return a2[1];
      for (let b2 = 0; b2 < a2.length; b2++) {
        const c = a2[b2];
        if ("Edge" == c[0]) return c;
      }
    }
    function module$contents$goog$labs$userAgent$engine_isVersionOrHigher(a2) {
      return 0 <= goog.string.internal.compareVersions(module$contents$goog$labs$userAgent$engine_getVersion(), a2);
    }
    function module$contents$goog$labs$userAgent$engine_getVersionForKey(a2, b2) {
      return (a2 = module$contents$goog$array_find(a2, function(c) {
        return b2 == c[0];
      })) && a2[1] || "";
    }
    goog.labs.userAgent.engine.getVersion = module$contents$goog$labs$userAgent$engine_getVersion;
    goog.labs.userAgent.engine.isEdge = module$contents$goog$labs$userAgent$engine_isEdge;
    goog.labs.userAgent.engine.isGecko = module$contents$goog$labs$userAgent$engine_isGecko;
    goog.labs.userAgent.engine.isPresto = module$contents$goog$labs$userAgent$engine_isPresto;
    goog.labs.userAgent.engine.isTrident = module$contents$goog$labs$userAgent$engine_isTrident;
    goog.labs.userAgent.engine.isVersionOrHigher = module$contents$goog$labs$userAgent$engine_isVersionOrHigher;
    goog.labs.userAgent.engine.isWebKit = module$contents$goog$labs$userAgent$engine_isWebKit;
    goog.labs.userAgent.platform = {};
    function module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform(a2 = false) {
      if (module$contents$goog$labs$userAgent$util_ASSUME_CLIENT_HINTS_SUPPORT) return true;
      if (!a2 && !(0, goog.labs.userAgent.useClientHints)()) return false;
      a2 = module$contents$goog$labs$userAgent$util_getUserAgentData();
      return !!a2 && !!a2.platform;
    }
    function module$contents$goog$labs$userAgent$platform_isAndroid() {
      return module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform() ? "Android" === module$contents$goog$labs$userAgent$util_getUserAgentData().platform : module$contents$goog$labs$userAgent$util_matchUserAgent("Android");
    }
    function module$contents$goog$labs$userAgent$platform_isIpod() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("iPod");
    }
    function module$contents$goog$labs$userAgent$platform_isIphone() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("iPhone") && !module$contents$goog$labs$userAgent$util_matchUserAgent("iPod") && !module$contents$goog$labs$userAgent$util_matchUserAgent("iPad");
    }
    function module$contents$goog$labs$userAgent$platform_isIpad() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("iPad");
    }
    function module$contents$goog$labs$userAgent$platform_isIos() {
      return module$contents$goog$labs$userAgent$platform_isIphone() || module$contents$goog$labs$userAgent$platform_isIpad() || module$contents$goog$labs$userAgent$platform_isIpod();
    }
    function module$contents$goog$labs$userAgent$platform_isMacintosh() {
      return module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform() ? "macOS" === module$contents$goog$labs$userAgent$util_getUserAgentData().platform : module$contents$goog$labs$userAgent$util_matchUserAgent("Macintosh");
    }
    function module$contents$goog$labs$userAgent$platform_isLinux() {
      return module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform() ? "Linux" === module$contents$goog$labs$userAgent$util_getUserAgentData().platform : module$contents$goog$labs$userAgent$util_matchUserAgent("Linux");
    }
    function module$contents$goog$labs$userAgent$platform_isWindows() {
      return module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform() ? "Windows" === module$contents$goog$labs$userAgent$util_getUserAgentData().platform : module$contents$goog$labs$userAgent$util_matchUserAgent("Windows");
    }
    function module$contents$goog$labs$userAgent$platform_isChromeOS() {
      return module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform() ? "Chrome OS" === module$contents$goog$labs$userAgent$util_getUserAgentData().platform : module$contents$goog$labs$userAgent$util_matchUserAgent("CrOS");
    }
    function module$contents$goog$labs$userAgent$platform_isChromecast() {
      return module$contents$goog$labs$userAgent$util_matchUserAgent("CrKey");
    }
    function module$contents$goog$labs$userAgent$platform_isKaiOS() {
      return module$contents$goog$labs$userAgent$util_matchUserAgentIgnoreCase("KaiOS");
    }
    function module$contents$goog$labs$userAgent$platform_getVersion() {
      var a2 = module$contents$goog$labs$userAgent$util_getUserAgent(), b2 = "";
      module$contents$goog$labs$userAgent$platform_isWindows() ? (b2 = /Windows (?:NT|Phone) ([0-9.]+)/, b2 = (a2 = b2.exec(a2)) ? a2[1] : "0.0") : module$contents$goog$labs$userAgent$platform_isIos() ? (b2 = /(?:iPhone|iPod|iPad|CPU)\s+OS\s+(\S+)/, b2 = (a2 = b2.exec(a2)) && a2[1].replace(/_/g, ".")) : module$contents$goog$labs$userAgent$platform_isMacintosh() ? (b2 = /Mac OS X ([0-9_.]+)/, b2 = (a2 = b2.exec(a2)) ? a2[1].replace(
        /_/g,
        "."
      ) : "10") : module$contents$goog$labs$userAgent$platform_isKaiOS() ? (b2 = /(?:KaiOS)\/(\S+)/i, b2 = (a2 = b2.exec(a2)) && a2[1]) : module$contents$goog$labs$userAgent$platform_isAndroid() ? (b2 = /Android\s+([^\);]+)(\)|;)/, b2 = (a2 = b2.exec(a2)) && a2[1]) : module$contents$goog$labs$userAgent$platform_isChromeOS() && (b2 = /(?:CrOS\s+(?:i686|x86_64)\s+([0-9.]+))/, b2 = (a2 = b2.exec(a2)) && a2[1]);
      return b2 || "";
    }
    function module$contents$goog$labs$userAgent$platform_isVersionOrHigher(a2) {
      return 0 <= goog.string.internal.compareVersions(module$contents$goog$labs$userAgent$platform_getVersion(), a2);
    }
    var module$contents$goog$labs$userAgent$platform_PlatformVersion = class {
      constructor() {
        this.preUachHasLoaded_ = false;
      }
      getIfLoaded() {
        if (module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform(true)) {
          const a2 = module$exports$goog$labs$userAgent$highEntropy$highEntropyData.platformVersion.getIfLoaded();
          return void 0 === a2 ? void 0 : new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(a2);
        }
        if (this.preUachHasLoaded_) return new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(module$contents$goog$labs$userAgent$platform_getVersion());
      }
      async load() {
        if (module$contents$goog$labs$userAgent$platform_useUserAgentDataPlatform(true)) return new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(await module$exports$goog$labs$userAgent$highEntropy$highEntropyData.platformVersion.load());
        this.preUachHasLoaded_ = true;
        return new module$exports$goog$labs$userAgent$highEntropy$highEntropyValue.Version(module$contents$goog$labs$userAgent$platform_getVersion());
      }
      resetForTesting() {
        module$exports$goog$labs$userAgent$highEntropy$highEntropyData.platformVersion.resetForTesting();
        this.preUachHasLoaded_ = false;
      }
    };
    var module$contents$goog$labs$userAgent$platform_version = new module$contents$goog$labs$userAgent$platform_PlatformVersion();
    goog.labs.userAgent.platform.getVersion = module$contents$goog$labs$userAgent$platform_getVersion;
    goog.labs.userAgent.platform.isAndroid = module$contents$goog$labs$userAgent$platform_isAndroid;
    goog.labs.userAgent.platform.isChromeOS = module$contents$goog$labs$userAgent$platform_isChromeOS;
    goog.labs.userAgent.platform.isChromecast = module$contents$goog$labs$userAgent$platform_isChromecast;
    goog.labs.userAgent.platform.isIos = module$contents$goog$labs$userAgent$platform_isIos;
    goog.labs.userAgent.platform.isIpad = module$contents$goog$labs$userAgent$platform_isIpad;
    goog.labs.userAgent.platform.isIphone = module$contents$goog$labs$userAgent$platform_isIphone;
    goog.labs.userAgent.platform.isIpod = module$contents$goog$labs$userAgent$platform_isIpod;
    goog.labs.userAgent.platform.isKaiOS = module$contents$goog$labs$userAgent$platform_isKaiOS;
    goog.labs.userAgent.platform.isLinux = module$contents$goog$labs$userAgent$platform_isLinux;
    goog.labs.userAgent.platform.isMacintosh = module$contents$goog$labs$userAgent$platform_isMacintosh;
    goog.labs.userAgent.platform.isVersionOrHigher = module$contents$goog$labs$userAgent$platform_isVersionOrHigher;
    goog.labs.userAgent.platform.isWindows = module$contents$goog$labs$userAgent$platform_isWindows;
    goog.labs.userAgent.platform.version = module$contents$goog$labs$userAgent$platform_version;
    goog.reflect = {};
    goog.reflect.object = function(a2, b2) {
      return b2;
    };
    goog.reflect.objectProperty = function(a2, b2) {
      return a2;
    };
    goog.reflect.sinkValue = function(a2) {
      goog.reflect.sinkValue[" "](a2);
      return a2;
    };
    goog.reflect.sinkValue[" "] = function() {
    };
    goog.reflect.canAccessProperty = function(a2, b2) {
      try {
        return goog.reflect.sinkValue(a2[b2]), true;
      } catch (c) {
      }
      return false;
    };
    goog.reflect.cache = function(a2, b2, c, d) {
      d = d ? d(b2) : b2;
      return Object.prototype.hasOwnProperty.call(a2, d) ? a2[d] : a2[d] = c(b2);
    };
    goog.userAgent = {};
    goog.userAgent.ASSUME_IE = false;
    goog.userAgent.ASSUME_EDGE = false;
    goog.userAgent.ASSUME_GECKO = false;
    goog.userAgent.ASSUME_WEBKIT = false;
    goog.userAgent.ASSUME_MOBILE_WEBKIT = false;
    goog.userAgent.ASSUME_OPERA = false;
    goog.userAgent.ASSUME_ANY_VERSION = false;
    goog.userAgent.BROWSER_KNOWN_ = goog.userAgent.ASSUME_IE || goog.userAgent.ASSUME_EDGE || goog.userAgent.ASSUME_GECKO || goog.userAgent.ASSUME_MOBILE_WEBKIT || goog.userAgent.ASSUME_WEBKIT || goog.userAgent.ASSUME_OPERA;
    goog.userAgent.getUserAgentString = function() {
      return module$contents$goog$labs$userAgent$util_getUserAgent();
    };
    goog.userAgent.getNavigatorTyped = function() {
      return goog.global.navigator || null;
    };
    goog.userAgent.getNavigator = function() {
      return goog.userAgent.getNavigatorTyped();
    };
    goog.userAgent.OPERA = goog.userAgent.BROWSER_KNOWN_ ? goog.userAgent.ASSUME_OPERA : module$contents$goog$labs$userAgent$browser_matchOpera();
    goog.userAgent.IE = goog.userAgent.BROWSER_KNOWN_ ? goog.userAgent.ASSUME_IE : module$contents$goog$labs$userAgent$browser_matchIE();
    goog.userAgent.EDGE = goog.userAgent.BROWSER_KNOWN_ ? goog.userAgent.ASSUME_EDGE : module$contents$goog$labs$userAgent$engine_isEdge();
    goog.userAgent.EDGE_OR_IE = goog.userAgent.EDGE || goog.userAgent.IE;
    goog.userAgent.GECKO = goog.userAgent.BROWSER_KNOWN_ ? goog.userAgent.ASSUME_GECKO : module$contents$goog$labs$userAgent$engine_isGecko();
    goog.userAgent.WEBKIT = goog.userAgent.BROWSER_KNOWN_ ? goog.userAgent.ASSUME_WEBKIT || goog.userAgent.ASSUME_MOBILE_WEBKIT : module$contents$goog$labs$userAgent$engine_isWebKit();
    goog.userAgent.isMobile_ = function() {
      return goog.userAgent.WEBKIT && module$contents$goog$labs$userAgent$util_matchUserAgent("Mobile");
    };
    goog.userAgent.MOBILE = goog.userAgent.ASSUME_MOBILE_WEBKIT || goog.userAgent.isMobile_();
    goog.userAgent.SAFARI = goog.userAgent.WEBKIT;
    goog.userAgent.determinePlatform_ = function() {
      var a2 = goog.userAgent.getNavigatorTyped();
      return a2 && a2.platform || "";
    };
    goog.userAgent.PLATFORM = goog.userAgent.determinePlatform_();
    goog.userAgent.ASSUME_MAC = false;
    goog.userAgent.ASSUME_WINDOWS = false;
    goog.userAgent.ASSUME_LINUX = false;
    goog.userAgent.ASSUME_X11 = false;
    goog.userAgent.ASSUME_ANDROID = false;
    goog.userAgent.ASSUME_IPHONE = false;
    goog.userAgent.ASSUME_IPAD = false;
    goog.userAgent.ASSUME_IPOD = false;
    goog.userAgent.ASSUME_KAIOS = false;
    goog.userAgent.PLATFORM_KNOWN_ = goog.userAgent.ASSUME_MAC || goog.userAgent.ASSUME_WINDOWS || goog.userAgent.ASSUME_LINUX || goog.userAgent.ASSUME_X11 || goog.userAgent.ASSUME_ANDROID || goog.userAgent.ASSUME_IPHONE || goog.userAgent.ASSUME_IPAD || goog.userAgent.ASSUME_IPOD;
    goog.userAgent.MAC = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_MAC : module$contents$goog$labs$userAgent$platform_isMacintosh();
    goog.userAgent.WINDOWS = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_WINDOWS : module$contents$goog$labs$userAgent$platform_isWindows();
    goog.userAgent.isLegacyLinux_ = function() {
      return module$contents$goog$labs$userAgent$platform_isLinux() || module$contents$goog$labs$userAgent$platform_isChromeOS();
    };
    goog.userAgent.LINUX = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_LINUX : goog.userAgent.isLegacyLinux_();
    goog.userAgent.isX11_ = function() {
      var a2 = goog.userAgent.getNavigatorTyped();
      return !!a2 && goog.string.internal.contains(a2.appVersion || "", "X11");
    };
    goog.userAgent.X11 = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_X11 : goog.userAgent.isX11_();
    goog.userAgent.ANDROID = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_ANDROID : module$contents$goog$labs$userAgent$platform_isAndroid();
    goog.userAgent.IPHONE = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_IPHONE : module$contents$goog$labs$userAgent$platform_isIphone();
    goog.userAgent.IPAD = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_IPAD : module$contents$goog$labs$userAgent$platform_isIpad();
    goog.userAgent.IPOD = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_IPOD : module$contents$goog$labs$userAgent$platform_isIpod();
    goog.userAgent.IOS = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_IPHONE || goog.userAgent.ASSUME_IPAD || goog.userAgent.ASSUME_IPOD : module$contents$goog$labs$userAgent$platform_isIos();
    goog.userAgent.KAIOS = goog.userAgent.PLATFORM_KNOWN_ ? goog.userAgent.ASSUME_KAIOS : module$contents$goog$labs$userAgent$platform_isKaiOS();
    goog.userAgent.determineVersion_ = function() {
      var a2 = "", b2 = goog.userAgent.getVersionRegexResult_();
      b2 && (a2 = b2 ? b2[1] : "");
      return goog.userAgent.IE && (b2 = goog.userAgent.getDocumentMode_(), null != b2 && b2 > parseFloat(a2)) ? String(b2) : a2;
    };
    goog.userAgent.getVersionRegexResult_ = function() {
      var a2 = goog.userAgent.getUserAgentString();
      if (goog.userAgent.GECKO) return /rv:([^\);]+)(\)|;)/.exec(a2);
      if (goog.userAgent.EDGE) return /Edge\/([\d\.]+)/.exec(a2);
      if (goog.userAgent.IE) return /\b(?:MSIE|rv)[: ]([^\);]+)(\)|;)/.exec(a2);
      if (goog.userAgent.WEBKIT) return /WebKit\/(\S+)/.exec(a2);
      if (goog.userAgent.OPERA) return /(?:Version)[ \/]?(\S+)/.exec(a2);
    };
    goog.userAgent.getDocumentMode_ = function() {
      var a2 = goog.global.document;
      return a2 ? a2.documentMode : void 0;
    };
    goog.userAgent.VERSION = goog.userAgent.determineVersion_();
    goog.userAgent.compare = function(a2, b2) {
      return goog.string.internal.compareVersions(a2, b2);
    };
    goog.userAgent.isVersionOrHigherCache_ = {};
    goog.userAgent.isVersionOrHigher = function(a2) {
      return goog.userAgent.ASSUME_ANY_VERSION || goog.reflect.cache(goog.userAgent.isVersionOrHigherCache_, a2, function() {
        return 0 <= goog.string.internal.compareVersions(goog.userAgent.VERSION, a2);
      });
    };
    goog.userAgent.isDocumentModeOrHigher = function(a2) {
      return Number(goog.userAgent.DOCUMENT_MODE) >= a2;
    };
    goog.userAgent.isDocumentMode = goog.userAgent.isDocumentModeOrHigher;
    goog.userAgent.DOCUMENT_MODE = (function() {
      if (goog.global.document && goog.userAgent.IE) {
        var a2 = goog.userAgent.getDocumentMode_();
        return a2 ? a2 : parseInt(goog.userAgent.VERSION, 10) || void 0;
      }
    })();
    goog.userAgent.product = {};
    goog.userAgent.product.ASSUME_FIREFOX = false;
    goog.userAgent.product.ASSUME_IPHONE = false;
    goog.userAgent.product.ASSUME_IPAD = false;
    goog.userAgent.product.ASSUME_ANDROID = false;
    goog.userAgent.product.ASSUME_CHROME = false;
    goog.userAgent.product.ASSUME_SAFARI = false;
    goog.userAgent.product.PRODUCT_KNOWN_ = goog.userAgent.ASSUME_IE || goog.userAgent.ASSUME_EDGE || goog.userAgent.ASSUME_OPERA || goog.userAgent.product.ASSUME_FIREFOX || goog.userAgent.product.ASSUME_IPHONE || goog.userAgent.product.ASSUME_IPAD || goog.userAgent.product.ASSUME_ANDROID || goog.userAgent.product.ASSUME_CHROME || goog.userAgent.product.ASSUME_SAFARI;
    goog.userAgent.product.OPERA = goog.userAgent.OPERA;
    goog.userAgent.product.IE = goog.userAgent.IE;
    goog.userAgent.product.EDGE = goog.userAgent.EDGE;
    goog.userAgent.product.FIREFOX = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_FIREFOX : module$contents$goog$labs$userAgent$browser_matchFirefox();
    goog.userAgent.product.isIphoneOrIpod_ = function() {
      return module$contents$goog$labs$userAgent$platform_isIphone() || module$contents$goog$labs$userAgent$platform_isIpod();
    };
    goog.userAgent.product.IPHONE = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_IPHONE : goog.userAgent.product.isIphoneOrIpod_();
    goog.userAgent.product.IPAD = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_IPAD : module$contents$goog$labs$userAgent$platform_isIpad();
    goog.userAgent.product.ANDROID = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_ANDROID : module$contents$goog$labs$userAgent$browser_matchAndroidBrowser();
    goog.userAgent.product.CHROME = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_CHROME : module$contents$goog$labs$userAgent$browser_matchChrome();
    goog.userAgent.product.isSafariDesktop_ = function() {
      return module$contents$goog$labs$userAgent$browser_matchSafari() && !module$contents$goog$labs$userAgent$platform_isIos();
    };
    goog.userAgent.product.SAFARI = goog.userAgent.product.PRODUCT_KNOWN_ ? goog.userAgent.product.ASSUME_SAFARI : goog.userAgent.product.isSafariDesktop_();
    goog.crypt.base64 = {};
    goog.crypt.base64.DEFAULT_ALPHABET_COMMON_ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    goog.crypt.base64.ENCODED_VALS = goog.crypt.base64.DEFAULT_ALPHABET_COMMON_ + "+/=";
    goog.crypt.base64.ENCODED_VALS_WEBSAFE = goog.crypt.base64.DEFAULT_ALPHABET_COMMON_ + "-_.";
    goog.crypt.base64.Alphabet = { DEFAULT: 0, NO_PADDING: 1, WEBSAFE: 2, WEBSAFE_DOT_PADDING: 3, WEBSAFE_NO_PADDING: 4 };
    goog.crypt.base64.paddingChars_ = "=.";
    goog.crypt.base64.isPadding_ = function(a2) {
      return goog.string.internal.contains(goog.crypt.base64.paddingChars_, a2);
    };
    goog.crypt.base64.byteToCharMaps_ = {};
    goog.crypt.base64.charToByteMap_ = null;
    goog.crypt.base64.ASSUME_NATIVE_SUPPORT_ = goog.userAgent.GECKO || goog.userAgent.WEBKIT;
    goog.crypt.base64.HAS_NATIVE_ENCODE_ = goog.crypt.base64.ASSUME_NATIVE_SUPPORT_ || "function" == typeof goog.global.btoa;
    goog.crypt.base64.HAS_NATIVE_DECODE_ = goog.crypt.base64.ASSUME_NATIVE_SUPPORT_ || !goog.userAgent.product.SAFARI && !goog.userAgent.IE && "function" == typeof goog.global.atob;
    goog.crypt.base64.encodeByteArray = function(a2, b2) {
      goog.asserts.assert(goog.isArrayLike(a2), "encodeByteArray takes an array as a parameter");
      void 0 === b2 && (b2 = goog.crypt.base64.Alphabet.DEFAULT);
      goog.crypt.base64.init_();
      b2 = goog.crypt.base64.byteToCharMaps_[b2];
      const c = Array(Math.floor(a2.length / 3)), d = b2[64] || "";
      let e = 0, f = 0;
      for (; e < a2.length - 2; e += 3) {
        var g = a2[e], h = a2[e + 1], l = a2[e + 2], k = b2[g >> 2];
        g = b2[(g & 3) << 4 | h >> 4];
        h = b2[(h & 15) << 2 | l >> 6];
        l = b2[l & 63];
        c[f++] = "" + k + g + h + l;
      }
      k = 0;
      l = d;
      switch (a2.length - e) {
        case 2:
          k = a2[e + 1], l = b2[(k & 15) << 2] || d;
        case 1:
          a2 = a2[e], c[f] = "" + b2[a2 >> 2] + b2[(a2 & 3) << 4 | k >> 4] + l + d;
      }
      return c.join("");
    };
    goog.crypt.base64.encodeBinaryString = function(a2, b2) {
      return goog.crypt.base64.encodeString(a2, b2, true);
    };
    goog.crypt.base64.encodeString = function(a2, b2, c) {
      return goog.crypt.base64.HAS_NATIVE_ENCODE_ && !b2 ? goog.global.btoa(a2) : goog.crypt.base64.encodeByteArray(goog.crypt.stringToByteArray(a2, c), b2);
    };
    goog.crypt.base64.encodeStringUtf8 = function(a2, b2) {
      return goog.crypt.base64.encodeText(a2, b2);
    };
    goog.crypt.base64.encodeText = function(a2, b2) {
      return goog.crypt.base64.HAS_NATIVE_ENCODE_ && !b2 ? goog.global.btoa(unescape(encodeURIComponent(a2))) : goog.crypt.base64.encodeByteArray(goog.crypt.stringToUtf8ByteArray(a2), b2);
    };
    goog.crypt.base64.decodeToBinaryString = function(a2, b2) {
      if (goog.crypt.base64.HAS_NATIVE_DECODE_ && !b2) return goog.global.atob(a2);
      var c = "";
      goog.crypt.base64.decodeStringInternal_(a2, function(d) {
        c += String.fromCharCode(d);
      });
      return c;
    };
    goog.crypt.base64.decodeString = goog.crypt.base64.decodeToBinaryString;
    goog.crypt.base64.decodeStringUtf8 = function(a2, b2) {
      return goog.crypt.base64.decodeToText(a2, b2);
    };
    goog.crypt.base64.decodeToText = function(a2, b2) {
      return decodeURIComponent(escape(goog.crypt.base64.decodeString(a2, b2)));
    };
    goog.crypt.base64.decodeStringToByteArray = function(a2, b2) {
      var c = [];
      goog.crypt.base64.decodeStringInternal_(a2, function(d) {
        c.push(d);
      });
      return c;
    };
    goog.crypt.base64.decodeStringToUint8Array = function(a2) {
      var b2 = a2.length, c = 3 * b2 / 4;
      c % 3 ? c = Math.floor(c) : goog.crypt.base64.isPadding_(a2[b2 - 1]) && (c = goog.crypt.base64.isPadding_(a2[b2 - 2]) ? c - 2 : c - 1);
      var d = new Uint8Array(c), e = 0;
      goog.crypt.base64.decodeStringInternal_(a2, function(f) {
        d[e++] = f;
      });
      return e !== c ? d.subarray(0, e) : d;
    };
    goog.crypt.base64.decodeStringInternal_ = function(a2, b2) {
      function c(l) {
        for (; d < a2.length; ) {
          var k = a2.charAt(d++), n = goog.crypt.base64.charToByteMap_[k];
          if (null != n) return n;
          if (!goog.string.internal.isEmptyOrWhitespace(k)) throw Error("Unknown base64 encoding at char: " + k);
        }
        return l;
      }
      goog.crypt.base64.init_();
      for (var d = 0; ; ) {
        var e = c(-1), f = c(0), g = c(64), h = c(64);
        if (64 === h && -1 === e) break;
        b2(e << 2 | f >> 4);
        64 != g && (b2(f << 4 & 240 | g >> 2), 64 != h && b2(g << 6 & 192 | h));
      }
    };
    goog.crypt.base64.init_ = function() {
      if (!goog.crypt.base64.charToByteMap_) {
        goog.crypt.base64.charToByteMap_ = {};
        for (var a2 = goog.crypt.base64.DEFAULT_ALPHABET_COMMON_.split(""), b2 = ["+/=", "+/", "-_=", "-_.", "-_"], c = 0; 5 > c; c++) {
          var d = a2.concat(b2[c].split(""));
          goog.crypt.base64.byteToCharMaps_[c] = d;
          for (var e = 0; e < d.length; e++) {
            var f = d[e], g = goog.crypt.base64.charToByteMap_[f];
            void 0 === g ? goog.crypt.base64.charToByteMap_[f] = e : goog.asserts.assert(g === e);
          }
        }
      }
    };
    jspb.BinaryConstants = {};
    var module$contents$jspb$BinaryConstants_FieldType = { INVALID: -1, DOUBLE: 1, FLOAT: 2, INT64: 3, UINT64: 4, INT32: 5, FIXED64: 6, FIXED32: 7, BOOL: 8, STRING: 9, GROUP: 10, MESSAGE: 11, BYTES: 12, UINT32: 13, ENUM: 14, SFIXED32: 15, SFIXED64: 16, SINT32: 17, SINT64: 18 };
    var module$contents$jspb$BinaryConstants_WireType = { INVALID: -1, VARINT: 0, FIXED64: 1, DELIMITED: 2, START_GROUP: 3, END_GROUP: 4, FIXED32: 5 };
    function module$contents$jspb$BinaryConstants_isValidWireType(a2) {
      return 0 <= a2 && 5 >= a2;
    }
    function module$contents$jspb$BinaryConstants_FieldTypeToWireType(a2) {
      switch (a2) {
        case module$contents$jspb$BinaryConstants_FieldType.INT32:
        case module$contents$jspb$BinaryConstants_FieldType.INT64:
        case module$contents$jspb$BinaryConstants_FieldType.UINT32:
        case module$contents$jspb$BinaryConstants_FieldType.UINT64:
        case module$contents$jspb$BinaryConstants_FieldType.SINT32:
        case module$contents$jspb$BinaryConstants_FieldType.SINT64:
        case module$contents$jspb$BinaryConstants_FieldType.BOOL:
        case module$contents$jspb$BinaryConstants_FieldType.ENUM:
          return module$contents$jspb$BinaryConstants_WireType.VARINT;
        case module$contents$jspb$BinaryConstants_FieldType.DOUBLE:
        case module$contents$jspb$BinaryConstants_FieldType.FIXED64:
        case module$contents$jspb$BinaryConstants_FieldType.SFIXED64:
          return module$contents$jspb$BinaryConstants_WireType.FIXED64;
        case module$contents$jspb$BinaryConstants_FieldType.STRING:
        case module$contents$jspb$BinaryConstants_FieldType.MESSAGE:
        case module$contents$jspb$BinaryConstants_FieldType.BYTES:
          return module$contents$jspb$BinaryConstants_WireType.DELIMITED;
        case module$contents$jspb$BinaryConstants_FieldType.FLOAT:
        case module$contents$jspb$BinaryConstants_FieldType.FIXED32:
        case module$contents$jspb$BinaryConstants_FieldType.SFIXED32:
          return module$contents$jspb$BinaryConstants_WireType.FIXED32;
        default:
          return module$contents$jspb$BinaryConstants_WireType.INVALID;
      }
    }
    var module$contents$jspb$BinaryConstants_INVALID_FIELD_NUMBER = -1;
    var module$contents$jspb$BinaryConstants_INVALID_TAG = -1;
    var module$contents$jspb$BinaryConstants_FLOAT32_EPS = 1401298464324817e-60;
    var module$contents$jspb$BinaryConstants_FLOAT32_MIN = 11754943508222875e-54;
    var module$contents$jspb$BinaryConstants_FLOAT32_MAX = 34028234663852886e22;
    var module$contents$jspb$BinaryConstants_FLOAT64_EPS = 5e-324;
    var module$contents$jspb$BinaryConstants_FLOAT64_MIN = 22250738585072014e-324;
    var module$contents$jspb$BinaryConstants_FLOAT64_MAX = 17976931348623157e292;
    var module$contents$jspb$BinaryConstants_TWO_TO_20 = 1048576;
    var module$contents$jspb$BinaryConstants_TWO_TO_23 = 8388608;
    var module$contents$jspb$BinaryConstants_TWO_TO_31 = 2147483648;
    var module$contents$jspb$BinaryConstants_TWO_TO_32 = 4294967296;
    var module$contents$jspb$BinaryConstants_TWO_TO_52 = 4503599627370496;
    var module$contents$jspb$BinaryConstants_TWO_TO_63 = 9223372036854776e3;
    var module$contents$jspb$BinaryConstants_TWO_TO_64 = 18446744073709552e3;
    var module$contents$jspb$BinaryConstants_ZERO_HASH = "\0\0\0\0\0\0\0\0";
    var module$contents$jspb$BinaryConstants_MESSAGE_SET_GROUP_NUMBER = 1;
    var module$contents$jspb$BinaryConstants_MESSAGE_SET_TYPE_ID_FIELD_NUMBER = 2;
    var module$contents$jspb$BinaryConstants_MESSAGE_SET_MESSAGE_FIELD_NUMBER = 3;
    var module$contents$jspb$BinaryConstants_MESSAGE_SET_MAX_TYPE_ID = 4294967294;
    jspb.BinaryConstants.FieldType = module$contents$jspb$BinaryConstants_FieldType;
    jspb.BinaryConstants.FieldTypeToWireType = module$contents$jspb$BinaryConstants_FieldTypeToWireType;
    jspb.BinaryConstants.FLOAT32_EPS = module$contents$jspb$BinaryConstants_FLOAT32_EPS;
    jspb.BinaryConstants.FLOAT32_MIN = module$contents$jspb$BinaryConstants_FLOAT32_MIN;
    jspb.BinaryConstants.FLOAT32_MAX = module$contents$jspb$BinaryConstants_FLOAT32_MAX;
    jspb.BinaryConstants.FLOAT64_EPS = module$contents$jspb$BinaryConstants_FLOAT64_EPS;
    jspb.BinaryConstants.FLOAT64_MIN = module$contents$jspb$BinaryConstants_FLOAT64_MIN;
    jspb.BinaryConstants.FLOAT64_MAX = module$contents$jspb$BinaryConstants_FLOAT64_MAX;
    jspb.BinaryConstants.INVALID_FIELD_NUMBER = module$contents$jspb$BinaryConstants_INVALID_FIELD_NUMBER;
    jspb.BinaryConstants.INVALID_TAG = module$contents$jspb$BinaryConstants_INVALID_TAG;
    jspb.BinaryConstants.MESSAGE_SET_GROUP_NUMBER = module$contents$jspb$BinaryConstants_MESSAGE_SET_GROUP_NUMBER;
    jspb.BinaryConstants.MESSAGE_SET_MAX_TYPE_ID = module$contents$jspb$BinaryConstants_MESSAGE_SET_MAX_TYPE_ID;
    jspb.BinaryConstants.MESSAGE_SET_MESSAGE_FIELD_NUMBER = module$contents$jspb$BinaryConstants_MESSAGE_SET_MESSAGE_FIELD_NUMBER;
    jspb.BinaryConstants.MESSAGE_SET_TYPE_ID_FIELD_NUMBER = module$contents$jspb$BinaryConstants_MESSAGE_SET_TYPE_ID_FIELD_NUMBER;
    jspb.BinaryConstants.TWO_TO_20 = module$contents$jspb$BinaryConstants_TWO_TO_20;
    jspb.BinaryConstants.TWO_TO_23 = module$contents$jspb$BinaryConstants_TWO_TO_23;
    jspb.BinaryConstants.TWO_TO_31 = module$contents$jspb$BinaryConstants_TWO_TO_31;
    jspb.BinaryConstants.TWO_TO_32 = module$contents$jspb$BinaryConstants_TWO_TO_32;
    jspb.BinaryConstants.TWO_TO_52 = module$contents$jspb$BinaryConstants_TWO_TO_52;
    jspb.BinaryConstants.TWO_TO_63 = module$contents$jspb$BinaryConstants_TWO_TO_63;
    jspb.BinaryConstants.TWO_TO_64 = module$contents$jspb$BinaryConstants_TWO_TO_64;
    jspb.BinaryConstants.WireType = module$contents$jspb$BinaryConstants_WireType;
    jspb.BinaryConstants.ZERO_HASH = module$contents$jspb$BinaryConstants_ZERO_HASH;
    jspb.BinaryConstants.isValidWireType = module$contents$jspb$BinaryConstants_isValidWireType;
    var module$exports$jspb$binary$errors = {};
    function module$contents$jspb$binary$errors_messageLengthMismatchError(a2, b2) {
      return Error(`Message parsing ended unexpectedly. Expected to read ${a2} bytes, instead read ${b2} bytes, either the data ended unexpectedly or the message misreported its own length`);
    }
    function module$contents$jspb$binary$errors_invalidWireTypeError(a2, b2) {
      return Error(`Invalid wire type: ${a2} (at position ${b2})`);
    }
    function module$contents$jspb$binary$errors_invalidFieldNumberError(a2, b2) {
      return Error(`Invalid field number: ${a2} (at position ${b2})`);
    }
    function module$contents$jspb$binary$errors_malformedBinaryBytesForMessageSet() {
      return Error("Malformed binary bytes for message set");
    }
    function module$contents$jspb$binary$errors_unmatchedStartGroupEofError() {
      return Error("Unmatched start-group tag: stream EOF");
    }
    function module$contents$jspb$binary$errors_unmatchedStartGroupError() {
      return Error("Unmatched end-group tag");
    }
    function module$contents$jspb$binary$errors_groupDidNotEndWithEndGroupError() {
      return Error("Group submessage did not end with an END_GROUP tag");
    }
    function module$contents$jspb$binary$errors_invalidVarintError() {
      return Error("Failed to read varint, encoding is invalid.");
    }
    function module$contents$jspb$binary$errors_readTooFarError(a2, b2) {
      return Error(`Tried to read past the end of the data ${b2} > ${a2}`);
    }
    function module$contents$jspb$binary$errors_negativeByteLengthError(a2) {
      return Error(`Tried to read a negative byte length: ${a2}`);
    }
    module$exports$jspb$binary$errors.messageLengthMismatchError = module$contents$jspb$binary$errors_messageLengthMismatchError;
    module$exports$jspb$binary$errors.groupDidNotEndWithEndGroupError = module$contents$jspb$binary$errors_groupDidNotEndWithEndGroupError;
    module$exports$jspb$binary$errors.invalidFieldNumberError = module$contents$jspb$binary$errors_invalidFieldNumberError;
    module$exports$jspb$binary$errors.invalidVarintError = module$contents$jspb$binary$errors_invalidVarintError;
    module$exports$jspb$binary$errors.invalidWireTypeError = module$contents$jspb$binary$errors_invalidWireTypeError;
    module$exports$jspb$binary$errors.malformedBinaryBytesForMessageSet = module$contents$jspb$binary$errors_malformedBinaryBytesForMessageSet;
    module$exports$jspb$binary$errors.negativeByteLengthError = module$contents$jspb$binary$errors_negativeByteLengthError;
    module$exports$jspb$binary$errors.readTooFarError = module$contents$jspb$binary$errors_readTooFarError;
    module$exports$jspb$binary$errors.unmatchedStartGroupError = module$contents$jspb$binary$errors_unmatchedStartGroupError;
    module$exports$jspb$binary$errors.unmatchedStartGroupEofError = module$contents$jspb$binary$errors_unmatchedStartGroupEofError;
    var module$exports$jspb$internal_options = {};
    function module$contents$jspb$internal_options_isBigIntAvailable() {
      return 2021 <= goog.FEATURESET_YEAR || "function" === typeof BigInt;
    }
    module$exports$jspb$internal_options.isBigIntAvailable = module$contents$jspb$internal_options_isBigIntAvailable;
    var module$exports$jspb$binary$bytesource = {};
    var module$exports$jspb$internal_bytes = {};
    module$exports$jspb$internal_bytes.SUPPORTS_UINT8ARRAY = 2018 <= goog.FEATURESET_YEAR || "undefined" !== typeof Uint8Array;
    var module$contents$jspb$internal_bytes_HANDLE_WEB_SAFE_ENCODINGS_WITH_ATOB_AND_BTOA = true;
    var module$contents$jspb$internal_bytes_CAN_USE_ATOB_AND_BTOA = true;
    var module$contents$jspb$internal_bytes_ASSUME_ATOB_AND_BTOA_AVAILABLE = 2018 <= goog.FEATURESET_YEAR;
    module$exports$jspb$internal_bytes.USE_ATOB_BTOA = module$contents$jspb$internal_bytes_CAN_USE_ATOB_AND_BTOA && (module$contents$jspb$internal_bytes_ASSUME_ATOB_AND_BTOA_AVAILABLE || !goog.userAgent.IE && "function" === typeof btoa);
    var module$contents$jspb$internal_bytes_UINT8ARRAY_MAX_SIZE_FOR_SPREAD = 10240;
    function module$contents$jspb$internal_bytes_encodeByteArray(a2) {
      if (!module$exports$jspb$internal_bytes.USE_ATOB_BTOA) return goog.crypt.base64.encodeByteArray(a2);
      let b2 = "", c = 0;
      const d = a2.length - module$contents$jspb$internal_bytes_UINT8ARRAY_MAX_SIZE_FOR_SPREAD;
      for (; c < d; ) b2 += String.fromCharCode.apply(null, a2.subarray(c, c += module$contents$jspb$internal_bytes_UINT8ARRAY_MAX_SIZE_FOR_SPREAD));
      b2 += String.fromCharCode.apply(null, c ? a2.subarray(c) : a2);
      return btoa(b2);
    }
    var module$contents$jspb$internal_bytes_WEBSAFE_BASE64_CHARS = /[-_.]/g;
    var module$contents$jspb$internal_bytes_websafeReplacer = { "-": "+", _: "/", ".": "=" };
    function module$contents$jspb$internal_bytes_replaceWebsafe(a2) {
      return module$contents$jspb$internal_bytes_websafeReplacer[a2] || "";
    }
    function module$contents$jspb$internal_bytes_replaceWebsafeString(a2) {
      return module$contents$jspb$internal_bytes_WEBSAFE_BASE64_CHARS.test(a2) ? a2.replace(module$contents$jspb$internal_bytes_WEBSAFE_BASE64_CHARS, module$contents$jspb$internal_bytes_replaceWebsafe) : a2;
    }
    function module$contents$jspb$internal_bytes_decodeByteArray(a2) {
      if (!module$exports$jspb$internal_bytes.USE_ATOB_BTOA) return goog.crypt.base64.decodeStringToUint8Array(a2);
      var b2 = a2;
      module$contents$jspb$internal_bytes_HANDLE_WEB_SAFE_ENCODINGS_WITH_ATOB_AND_BTOA && (b2 = module$contents$jspb$internal_bytes_replaceWebsafeString(b2));
      let c;
      if (goog.DEBUG) try {
        c = atob(b2);
      } catch (d) {
        throw Error(`invalid encoding '${a2}': ${d}`);
      }
      else c = atob(b2);
      a2 = new Uint8Array(c.length);
      for (b2 = 0; b2 < c.length; b2++) a2[b2] = c.charCodeAt(b2);
      return a2;
    }
    function module$contents$jspb$internal_bytes_dataAsU8(a2) {
      if (null == a2 || module$contents$jspb$internal_bytes_isU8(a2)) return a2;
      if ("string" === typeof a2) return module$contents$jspb$internal_bytes_decodeByteArray(a2);
      (0, goog.asserts.fail)("Cannot coerce to Uint8Array: " + goog.typeOf(a2));
      return null;
    }
    function module$contents$jspb$internal_bytes_isU8(a2) {
      return module$exports$jspb$internal_bytes.SUPPORTS_UINT8ARRAY && null != a2 && a2 instanceof Uint8Array;
    }
    function module$contents$jspb$internal_bytes_uint8ArrayEquals(a2, b2) {
      const c = a2.length;
      if (c !== b2.length) return false;
      for (let d = 0; d < c; d++) if (a2[d] !== b2[d]) return false;
      return true;
    }
    module$exports$jspb$internal_bytes.I_AM_INTERNAL = {};
    module$exports$jspb$internal_bytes.encodeByteArray = module$contents$jspb$internal_bytes_encodeByteArray;
    module$exports$jspb$internal_bytes.decodeByteArray = module$contents$jspb$internal_bytes_decodeByteArray;
    module$exports$jspb$internal_bytes.dataAsU8 = module$contents$jspb$internal_bytes_dataAsU8;
    module$exports$jspb$internal_bytes.isU8 = module$contents$jspb$internal_bytes_isU8;
    module$exports$jspb$internal_bytes.replaceWebsafeString = module$contents$jspb$internal_bytes_replaceWebsafeString;
    module$exports$jspb$internal_bytes.uint8ArrayEquals = module$contents$jspb$internal_bytes_uint8ArrayEquals;
    jspb.binary = {};
    jspb.binary.utf8 = {};
    var module$contents$jspb$binary$utf8_USE_TEXT_ENCODING = true;
    var module$contents$jspb$binary$utf8_ASSUME_TEXT_ENCODING_AVAILABLE = 2020 <= goog.FEATURESET_YEAR;
    var module$contents$jspb$binary$utf8_MIN_SURROGATE = 55296;
    var module$contents$jspb$binary$utf8_MIN_HIGH_SURROGATE = module$contents$jspb$binary$utf8_MIN_SURROGATE;
    var module$contents$jspb$binary$utf8_MAX_HIGH_SURROGATE = 56319;
    var module$contents$jspb$binary$utf8_MIN_LOW_SURROGATE = 56320;
    var module$contents$jspb$binary$utf8_MAX_LOW_SURROGATE = 57343;
    var module$contents$jspb$binary$utf8_MAX_SURROGATE = module$contents$jspb$binary$utf8_MAX_LOW_SURROGATE;
    function module$contents$jspb$binary$utf8_isNotTrailingByte(a2) {
      return 128 !== (a2 & 192);
    }
    function module$contents$jspb$binary$utf8_invalid(a2, b2) {
      if (a2) throw Error("Invalid UTF8");
      b2.push(65533);
    }
    function module$contents$jspb$binary$utf8_codeUnitsToString(a2, b2) {
      b2 = String.fromCharCode.apply(null, b2);
      return null == a2 ? b2 : a2 + b2;
    }
    function module$contents$jspb$binary$utf8_polyfillDecodeUtf8(a2, b2, c, d) {
      c = b2 + c;
      const e = [];
      let f = null;
      let g, h, l;
      for (; b2 < c; ) {
        var k = a2[b2++];
        128 > k ? e.push(k) : 224 > k ? b2 >= c ? module$contents$jspb$binary$utf8_invalid(d, e) : (g = a2[b2++], 194 > k || module$contents$jspb$binary$utf8_isNotTrailingByte(g) ? (b2--, module$contents$jspb$binary$utf8_invalid(d, e)) : (k = (k & 31) << 6 | g & 63, (0, goog.asserts.assert)(128 <= k && 2047 >= k), e.push(k))) : 240 > k ? b2 >= c - 1 ? module$contents$jspb$binary$utf8_invalid(d, e) : (g = a2[b2++], module$contents$jspb$binary$utf8_isNotTrailingByte(g) || 224 === k && 160 > g || 237 === k && 160 <= g || module$contents$jspb$binary$utf8_isNotTrailingByte(h = a2[b2++]) ? (b2--, module$contents$jspb$binary$utf8_invalid(d, e)) : (k = (k & 15) << 12 | (g & 63) << 6 | h & 63, (0, goog.asserts.assert)(2048 <= k && 65535 >= k), (0, goog.asserts.assert)(k < module$contents$jspb$binary$utf8_MIN_SURROGATE || k > module$contents$jspb$binary$utf8_MAX_LOW_SURROGATE), e.push(k))) : 244 >= k ? b2 >= c - 2 ? module$contents$jspb$binary$utf8_invalid(d, e) : (g = a2[b2++], module$contents$jspb$binary$utf8_isNotTrailingByte(g) || 0 !== (k << 28) + (g - 144) >> 30 || module$contents$jspb$binary$utf8_isNotTrailingByte(h = a2[b2++]) || module$contents$jspb$binary$utf8_isNotTrailingByte(l = a2[b2++]) ? (b2--, module$contents$jspb$binary$utf8_invalid(d, e)) : (k = (k & 7) << 18 | (g & 63) << 12 | (h & 63) << 6 | l & 63, (0, goog.asserts.assert)(65536 <= k && 1114111 >= k), k -= 65536, e.push((k >> 10 & 1023) + module$contents$jspb$binary$utf8_MIN_SURROGATE, (k & 1023) + module$contents$jspb$binary$utf8_MIN_LOW_SURROGATE))) : module$contents$jspb$binary$utf8_invalid(d, e);
        8192 <= e.length && (f = module$contents$jspb$binary$utf8_codeUnitsToString(
          f,
          e
        ), e.length = 0);
      }
      (0, goog.asserts.assert)(b2 === c, `expected ${b2} === ${c}`);
      return module$contents$jspb$binary$utf8_codeUnitsToString(f, e);
    }
    var module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing_ = 2020 <= goog.FEATURESET_YEAR ? true : void 0;
    function module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing(a2) {
      if (void 0 === module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing_) {
        try {
          a2.decode(new Uint8Array([128]));
        } catch (b2) {
        }
        try {
          a2.decode(new Uint8Array([97])), module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing_ = true;
        } catch (b2) {
          module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing_ = false;
        }
      }
      return module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing_;
    }
    var module$contents$jspb$binary$utf8_fatalDecoderInstance;
    function module$contents$jspb$binary$utf8_getFatalDecoderInstance() {
      let a2 = module$contents$jspb$binary$utf8_fatalDecoderInstance;
      a2 || (a2 = module$contents$jspb$binary$utf8_fatalDecoderInstance = new TextDecoder("utf-8", { fatal: true }));
      return a2;
    }
    var module$contents$jspb$binary$utf8_nonFatalDecoderInstance;
    function module$contents$jspb$binary$utf8_getNonFatalDecoderInstance() {
      let a2 = module$contents$jspb$binary$utf8_nonFatalDecoderInstance;
      a2 || (a2 = module$contents$jspb$binary$utf8_nonFatalDecoderInstance = new TextDecoder("utf-8", { fatal: false }));
      return a2;
    }
    function module$contents$jspb$binary$utf8_subarray(a2, b2, c) {
      return 0 === b2 && c === a2.length ? a2 : a2.subarray(b2, c);
    }
    function module$contents$jspb$binary$utf8_textDecoderDecodeUtf8(a2, b2, c, d) {
      const e = d ? module$contents$jspb$binary$utf8_getFatalDecoderInstance() : module$contents$jspb$binary$utf8_getNonFatalDecoderInstance();
      a2 = module$contents$jspb$binary$utf8_subarray(a2, b2, b2 + c);
      try {
        return e.decode(a2);
      } catch (f) {
        throw d && !module$contents$jspb$binary$utf8_isFatalTextDecoderCachableAfterThrowing(e) && (module$contents$jspb$binary$utf8_fatalDecoderInstance = void 0), f;
      }
    }
    var module$contents$jspb$binary$utf8_useTextDecoderDecode = module$contents$jspb$binary$utf8_USE_TEXT_ENCODING && (module$contents$jspb$binary$utf8_ASSUME_TEXT_ENCODING_AVAILABLE || "undefined" !== typeof TextDecoder);
    function module$contents$jspb$binary$utf8_decodeUtf8(a2, b2, c, d) {
      return module$contents$jspb$binary$utf8_useTextDecoderDecode ? module$contents$jspb$binary$utf8_textDecoderDecodeUtf8(a2, b2, c, d) : module$contents$jspb$binary$utf8_polyfillDecodeUtf8(a2, b2, c, d);
    }
    var module$contents$jspb$binary$utf8_textEncoderInstance;
    function module$contents$jspb$binary$utf8_textEncoderEncode(a2, b2) {
      b2 && module$contents$jspb$binary$utf8_checkWellFormed(a2);
      return (module$contents$jspb$binary$utf8_textEncoderInstance || (module$contents$jspb$binary$utf8_textEncoderInstance = new TextEncoder())).encode(a2);
    }
    var module$contents$jspb$binary$utf8_IS_WELL_FORMED = "isWellFormed";
    var module$contents$jspb$binary$utf8_HAS_WELL_FORMED_METHOD = 2023 < goog.FEATURESET_YEAR || "function" === typeof String.prototype[module$contents$jspb$binary$utf8_IS_WELL_FORMED];
    function module$contents$jspb$binary$utf8_checkWellFormed(a2) {
      if (module$contents$jspb$binary$utf8_HAS_WELL_FORMED_METHOD ? !a2[module$contents$jspb$binary$utf8_IS_WELL_FORMED]() : /(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])/.test(a2)) throw Error("Found an unpaired surrogate");
    }
    function module$contents$jspb$binary$utf8_polyfillEncode(a2, b2) {
      let c = 0;
      const d = new Uint8Array(3 * a2.length);
      for (let f = 0; f < a2.length; f++) {
        var e = a2.charCodeAt(f);
        if (128 > e) d[c++] = e;
        else {
          if (2048 > e) d[c++] = e >> 6 | 192;
          else {
            (0, goog.asserts.assert)(65536 > e);
            if (e >= module$contents$jspb$binary$utf8_MIN_SURROGATE && e <= module$contents$jspb$binary$utf8_MAX_LOW_SURROGATE) {
              if (e <= module$contents$jspb$binary$utf8_MAX_HIGH_SURROGATE && f < a2.length) {
                const g = a2.charCodeAt(++f);
                if (g >= module$contents$jspb$binary$utf8_MIN_LOW_SURROGATE && g <= module$contents$jspb$binary$utf8_MAX_LOW_SURROGATE) {
                  e = 1024 * (e - module$contents$jspb$binary$utf8_MIN_SURROGATE) + g - module$contents$jspb$binary$utf8_MIN_LOW_SURROGATE + 65536;
                  d[c++] = e >> 18 | 240;
                  d[c++] = e >> 12 & 63 | 128;
                  d[c++] = e >> 6 & 63 | 128;
                  d[c++] = e & 63 | 128;
                  continue;
                } else f--;
              }
              if (b2) throw Error("Found an unpaired surrogate");
              e = 65533;
            }
            d[c++] = e >> 12 | 224;
            d[c++] = e >> 6 & 63 | 128;
          }
          d[c++] = e & 63 | 128;
        }
      }
      return module$contents$jspb$binary$utf8_subarray(d, 0, c);
    }
    var module$contents$jspb$binary$utf8_useTextEncoderEncode = module$contents$jspb$binary$utf8_USE_TEXT_ENCODING && (module$contents$jspb$binary$utf8_ASSUME_TEXT_ENCODING_AVAILABLE || "undefined" !== typeof TextEncoder);
    function module$contents$jspb$binary$utf8_encodeUtf8(a2, b2 = false) {
      (0, goog.asserts.assertString)(a2);
      return module$contents$jspb$binary$utf8_useTextEncoderEncode ? module$contents$jspb$binary$utf8_textEncoderEncode(a2, b2) : module$contents$jspb$binary$utf8_polyfillEncode(a2, b2);
    }
    jspb.binary.utf8.decodeUtf8 = module$contents$jspb$binary$utf8_decodeUtf8;
    jspb.binary.utf8.encodeUtf8 = module$contents$jspb$binary$utf8_encodeUtf8;
    jspb.binary.utf8.checkWellFormed = module$contents$jspb$binary$utf8_checkWellFormed;
    jspb.binary.utf8.textDecoderDecodeUtf8 = module$contents$jspb$binary$utf8_textDecoderDecodeUtf8;
    jspb.binary.utf8.polyfillDecodeUtf8 = module$contents$jspb$binary$utf8_polyfillDecodeUtf8;
    jspb.binary.utf8.textEncoderEncode = module$contents$jspb$binary$utf8_textEncoderEncode;
    jspb.binary.utf8.polyfillEncode = module$contents$jspb$binary$utf8_polyfillEncode;
    jspb.bytestring = {};
    var module$contents$jspb$bytestring_ByteString = class _module$contents$jspb$bytestring_ByteString {
      static fromBase64(a2) {
        (0, goog.asserts.assertString)(a2);
        return a2 ? new _module$contents$jspb$bytestring_ByteString(a2, module$exports$jspb$internal_bytes.I_AM_INTERNAL) : _module$contents$jspb$bytestring_ByteString.empty();
      }
      static fromUint8Array(a2) {
        (0, goog.asserts.assert)(a2 instanceof Uint8Array || Array.isArray(a2));
        return a2.length ? new _module$contents$jspb$bytestring_ByteString(new Uint8Array(a2), module$exports$jspb$internal_bytes.I_AM_INTERNAL) : _module$contents$jspb$bytestring_ByteString.empty();
      }
      static fromStringUtf8(a2) {
        (0, goog.asserts.assertString)(a2);
        return a2.length ? new _module$contents$jspb$bytestring_ByteString(module$contents$jspb$binary$utf8_encodeUtf8(a2, true), module$exports$jspb$internal_bytes.I_AM_INTERNAL) : _module$contents$jspb$bytestring_ByteString.empty();
      }
      static async fromBlob(a2) {
        (0, goog.asserts.assertInstanceof)(a2, Blob);
        if (0 === a2.size) return _module$contents$jspb$bytestring_ByteString.empty();
        a2 = await a2.arrayBuffer();
        return new _module$contents$jspb$bytestring_ByteString(new Uint8Array(a2), module$exports$jspb$internal_bytes.I_AM_INTERNAL);
      }
      static empty() {
        return module$contents$jspb$bytestring_emptyByteString || (module$contents$jspb$bytestring_emptyByteString = new _module$contents$jspb$bytestring_ByteString(null, module$exports$jspb$internal_bytes.I_AM_INTERNAL));
      }
      asBase64() {
        const a2 = this.value_;
        return null == a2 ? "" : "string" === typeof a2 ? a2 : this.value_ = module$contents$jspb$internal_bytes_encodeByteArray(a2);
      }
      asUint8Array() {
        return new Uint8Array(this.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL) || 0);
      }
      isEmpty() {
        return null == this.value_;
      }
      sizeBytes() {
        const a2 = this.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL);
        return a2 ? a2.length : 0;
      }
      unsignedByteAt(a2) {
        (0, goog.asserts.assertNumber)(a2);
        (0, goog.asserts.assert)(0 <= a2, "index %s should be non-negative", a2);
        const b2 = this.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL);
        (0, goog.asserts.assert)(a2 < b2.length, "index %s must be less than %s", a2, b2.length);
        return b2[a2];
      }
      signedByteAt(a2) {
        return this.unsignedByteAt(a2) << 24 >> 24;
      }
      asStringUtf8({ parsingErrorsAreFatal: a2 = true } = {}) {
        const b2 = this.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL);
        return b2 ? module$contents$jspb$binary$utf8_decodeUtf8(
          b2,
          0,
          b2.length,
          a2
        ) : "";
      }
      asBlob(a2) {
        const b2 = this.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL);
        return b2 ? new Blob([b2], a2) : new Blob([], a2);
      }
      internalBytesUnsafe(a2) {
        module$contents$jspb$bytestring_checkAllowedCaller(a2);
        a2 = module$contents$jspb$internal_bytes_dataAsU8(this.value_);
        return null == a2 ? a2 : this.value_ = a2;
      }
      internalUnwrap(a2) {
        module$contents$jspb$bytestring_checkAllowedCaller(a2);
        return this.value_ || "";
      }
      constructor(a2, b2) {
        module$contents$jspb$bytestring_checkAllowedCaller(b2);
        this.value_ = a2;
        if (null != a2 && 0 === a2.length) throw Error("ByteString should be constructed with non-empty values");
      }
    };
    var module$contents$jspb$bytestring_emptyByteString;
    function module$contents$jspb$bytestring_checkAllowedCaller(a2) {
      if (a2 !== module$exports$jspb$internal_bytes.I_AM_INTERNAL) throw Error("illegal external caller");
    }
    jspb.bytestring.ByteString = module$contents$jspb$bytestring_ByteString;
    var module$exports$jspb$unsafe_bytestring = {};
    function module$contents$jspb$unsafe_bytestring_unsafeByteStringFromUint8Array(a2) {
      (0, goog.asserts.assertInstanceof)(a2, Uint8Array);
      return 0 == a2.length ? module$contents$jspb$bytestring_ByteString.empty() : new module$contents$jspb$bytestring_ByteString(a2, module$exports$jspb$internal_bytes.I_AM_INTERNAL);
    }
    function module$contents$jspb$unsafe_bytestring_unsafeUint8ArrayFromByteString(a2) {
      (0, goog.asserts.assertInstanceof)(a2, module$contents$jspb$bytestring_ByteString);
      return a2.internalBytesUnsafe(module$exports$jspb$internal_bytes.I_AM_INTERNAL) || new Uint8Array(0);
    }
    function module$contents$jspb$unsafe_bytestring_unsafeUnwrapByteString(a2) {
      (0, goog.asserts.assertInstanceof)(a2, module$contents$jspb$bytestring_ByteString);
      return a2.internalUnwrap(module$exports$jspb$internal_bytes.I_AM_INTERNAL);
    }
    module$exports$jspb$unsafe_bytestring.unsafeByteStringFromUint8Array = module$contents$jspb$unsafe_bytestring_unsafeByteStringFromUint8Array;
    module$exports$jspb$unsafe_bytestring.unsafeUint8ArrayFromByteString = module$contents$jspb$unsafe_bytestring_unsafeUint8ArrayFromByteString;
    module$exports$jspb$unsafe_bytestring.unsafeUnwrapByteString = module$contents$jspb$unsafe_bytestring_unsafeUnwrapByteString;
    jspb.utils = {};
    var module$contents$jspb$utils_SUPPORTS_UINT8ARRAY_SLICING = 2018 <= goog.FEATURESET_YEAR || "function" === typeof Uint8Array.prototype.slice;
    var module$contents$jspb$utils_MAX_SCRATCHPAD_BYTES = 8;
    function module$contents$jspb$utils_sliceUint8Array(a2, b2, c) {
      return b2 === c ? new Uint8Array(0) : module$contents$jspb$utils_SUPPORTS_UINT8ARRAY_SLICING ? a2.slice(b2, c) : new Uint8Array(a2.subarray(b2, c));
    }
    var module$contents$jspb$utils_split64Low = 0;
    var module$contents$jspb$utils_split64High = 0;
    var module$contents$jspb$utils_scratchpad;
    function module$contents$jspb$utils_splitUint64(a2) {
      const b2 = a2 >>> 0;
      a2 = (a2 - b2) / module$contents$jspb$BinaryConstants_TWO_TO_32 >>> 0;
      module$contents$jspb$utils_split64Low = b2;
      module$contents$jspb$utils_split64High = a2;
    }
    function module$contents$jspb$utils_splitInt64(a2) {
      if (0 > a2) {
        module$contents$jspb$utils_splitUint64(0 - a2);
        const [b2, c] = module$contents$jspb$utils_negate(module$contents$jspb$utils_split64Low, module$contents$jspb$utils_split64High);
        module$contents$jspb$utils_split64Low = b2 >>> 0;
        module$contents$jspb$utils_split64High = c >>> 0;
      } else module$contents$jspb$utils_splitUint64(a2);
    }
    function module$contents$jspb$utils_splitZigzag64(a2) {
      const b2 = 0 > a2;
      a2 = 2 * Math.abs(a2);
      module$contents$jspb$utils_splitUint64(a2);
      a2 = module$contents$jspb$utils_split64Low;
      let c = module$contents$jspb$utils_split64High;
      b2 && (0 == a2 ? 0 == c ? c = a2 = 4294967295 : (c--, a2 = 4294967295) : a2--);
      module$contents$jspb$utils_split64Low = a2;
      module$contents$jspb$utils_split64High = c;
    }
    function module$contents$jspb$utils_getScratchpad(a2) {
      (0, goog.asserts.assert)(a2 <= module$contents$jspb$utils_MAX_SCRATCHPAD_BYTES);
      return module$contents$jspb$utils_scratchpad || (module$contents$jspb$utils_scratchpad = new DataView(new ArrayBuffer(module$contents$jspb$utils_MAX_SCRATCHPAD_BYTES)));
    }
    function module$contents$jspb$utils_splitFloat32(a2) {
      const b2 = module$contents$jspb$utils_getScratchpad(4);
      b2.setFloat32(0, +a2, true);
      module$contents$jspb$utils_split64High = 0;
      module$contents$jspb$utils_split64Low = b2.getUint32(0, true);
    }
    function module$contents$jspb$utils_splitFloat64(a2) {
      const b2 = module$contents$jspb$utils_getScratchpad(8);
      b2.setFloat64(0, +a2, true);
      module$contents$jspb$utils_split64Low = b2.getUint32(0, true);
      module$contents$jspb$utils_split64High = b2.getUint32(4, true);
    }
    function module$contents$jspb$utils_splitBytes64(a2) {
      const [b2, c, d, e, f, g, h, l] = a2;
      module$contents$jspb$utils_split64Low = b2 + (c << 8) + (d << 16) + (e << 24) >>> 0;
      module$contents$jspb$utils_split64High = f + (g << 8) + (h << 16) + (l << 24) >>> 0;
    }
    function module$contents$jspb$utils_joinUint64(a2, b2) {
      const c = b2 * module$contents$jspb$BinaryConstants_TWO_TO_32 + (a2 >>> 0);
      return Number.isSafeInteger(c) ? c : module$contents$jspb$utils_joinUnsignedDecimalString(a2, b2);
    }
    function module$contents$jspb$utils_joinInt64(a2, b2) {
      const c = b2 & 2147483648;
      c && (a2 = ~a2 + 1 >>> 0, b2 = ~b2 >>> 0, 0 == a2 && (b2 = b2 + 1 >>> 0));
      a2 = module$contents$jspb$utils_joinUint64(a2, b2);
      return "number" === typeof a2 ? c ? -a2 : a2 : c ? "-" + a2 : a2;
    }
    function module$contents$jspb$utils_toZigzag32(a2) {
      return (a2 << 1 ^ a2 >> 31) >>> 0;
    }
    function module$contents$jspb$utils_toZigzag64(a2, b2, c) {
      const d = b2 >> 31;
      b2 = (b2 << 1 | a2 >>> 31) ^ d;
      a2 = a2 << 1 ^ d;
      return c(a2, b2);
    }
    function module$contents$jspb$utils_joinZigzag64(a2, b2) {
      return module$contents$jspb$utils_fromZigzag64(a2, b2, module$contents$jspb$utils_joinInt64);
    }
    function module$contents$jspb$utils_fromZigzag32(a2) {
      return a2 >>> 1 ^ -(a2 & 1);
    }
    function module$contents$jspb$utils_fromZigzag64(a2, b2, c) {
      const d = -(a2 & 1);
      a2 = (a2 >>> 1 | b2 << 31) ^ d;
      b2 = b2 >>> 1 ^ d;
      return c(a2, b2);
    }
    function module$contents$jspb$utils_joinFloat32(a2, b2) {
      b2 = 2 * (a2 >> 31) + 1;
      const c = a2 >>> 23 & 255;
      a2 &= 8388607;
      return 255 == c ? a2 ? NaN : Infinity * b2 : 0 == c ? b2 * Math.pow(2, -149) * a2 : b2 * Math.pow(2, c - 150) * (a2 + Math.pow(2, 23));
    }
    function module$contents$jspb$utils_joinFloat64(a2, b2) {
      const c = 2 * (b2 >> 31) + 1, d = b2 >>> 20 & 2047;
      a2 = module$contents$jspb$BinaryConstants_TWO_TO_32 * (b2 & 1048575) + a2;
      return 2047 == d ? a2 ? NaN : Infinity * c : 0 == d ? c * Math.pow(2, -1074) * a2 : c * Math.pow(2, d - 1075) * (a2 + module$contents$jspb$BinaryConstants_TWO_TO_52);
    }
    function module$contents$jspb$utils_joinUnsignedDecimalString(a2, b2) {
      b2 >>>= 0;
      a2 >>>= 0;
      return 2097151 >= b2 ? "" + (module$contents$jspb$BinaryConstants_TWO_TO_32 * b2 + a2) : module$contents$jspb$internal_options_isBigIntAvailable() ? "" + (BigInt(b2) << BigInt(32) | BigInt(a2)) : module$contents$jspb$utils_joinUnsignedDecimalStringFallback(a2, b2);
    }
    function module$contents$jspb$utils_joinUnsignedDecimalStringFallback(a2, b2) {
      var c = (a2 >>> 24 | b2 << 8) & module$contents$jspb$utils_LOW_24_BITS;
      b2 = b2 >> 16 & module$contents$jspb$utils_LOW_16_BITS;
      a2 = (a2 & module$contents$jspb$utils_LOW_24_BITS) + 6777216 * c + 6710656 * b2;
      c += 8147497 * b2;
      b2 *= 2;
      1e7 <= a2 && (c += a2 / 1e7 >>> 0, a2 %= 1e7);
      1e7 <= c && (b2 += c / 1e7 >>> 0, c %= 1e7);
      (0, goog.asserts.assert)(b2);
      return b2 + module$contents$jspb$utils_decimalFrom1e7WithLeadingZeros(c) + module$contents$jspb$utils_decimalFrom1e7WithLeadingZeros(a2);
    }
    function module$contents$jspb$utils_decimalFrom1e7WithLeadingZeros(a2) {
      a2 = String(a2);
      return "0000000".slice(a2.length) + a2;
    }
    function module$contents$jspb$utils_joinSignedDecimalString(a2, b2) {
      return b2 & 2147483648 ? module$contents$jspb$internal_options_isBigIntAvailable() ? "" + (BigInt(b2 | 0) << BigInt(32) | BigInt(a2 >>> 0)) : module$contents$jspb$utils_joinNegativeDecimalStringFallback(a2, b2) : module$contents$jspb$utils_joinUnsignedDecimalString(a2, b2);
    }
    function module$contents$jspb$utils_joinSignedNumberOrDecimalString(a2, b2) {
      const c = module$contents$jspb$utils_joinInt64(a2, b2);
      return Number.isSafeInteger(c) ? c : module$contents$jspb$utils_joinSignedDecimalString(a2, b2);
    }
    function module$contents$jspb$utils_joinUnsignedNumberOrDecimalString(a2, b2) {
      b2 >>>= 0;
      const c = module$contents$jspb$utils_joinUint64(a2, b2);
      return Number.isSafeInteger(c) ? c : module$contents$jspb$utils_joinUnsignedDecimalString(a2, b2);
    }
    function module$contents$jspb$utils_joinNegativeDecimalStringFallback(a2, b2) {
      const [c, d] = module$contents$jspb$utils_negate(a2, b2);
      a2 = c;
      b2 = d;
      return "-" + module$contents$jspb$utils_joinUnsignedDecimalString(a2, b2);
    }
    function module$contents$jspb$utils_splitDecimalString(a2) {
      (0, goog.asserts.assert)(0 < a2.length);
      a2.length < module$contents$jspb$utils_MAX_SAFE_INTEGER_DECIMAL_LENGTH ? module$contents$jspb$utils_splitInt64(Number(a2)) : module$contents$jspb$internal_options_isBigIntAvailable() ? (a2 = BigInt(a2), module$contents$jspb$utils_split64Low = Number(a2 & BigInt(module$contents$jspb$utils_ALL_32_BITS)) >>> 0, module$contents$jspb$utils_split64High = Number(a2 >> BigInt(32) & BigInt(module$contents$jspb$utils_ALL_32_BITS))) : module$contents$jspb$utils_splitDecimalStringFallback(a2);
    }
    function module$contents$jspb$utils_splitDecimalStringFallback(a2) {
      (0, goog.asserts.assert)(0 < a2.length);
      const b2 = +("-" === a2[0]);
      module$contents$jspb$utils_split64High = module$contents$jspb$utils_split64Low = 0;
      const c = a2.length;
      for (let d = 0 + b2, e = (c - b2) % 6 + b2; e <= c; d = e, e += 6) {
        const f = Number(a2.slice(d, e));
        module$contents$jspb$utils_split64High *= 1e6;
        module$contents$jspb$utils_split64Low = 1e6 * module$contents$jspb$utils_split64Low + f;
        module$contents$jspb$utils_split64Low >= module$contents$jspb$BinaryConstants_TWO_TO_32 && (module$contents$jspb$utils_split64High += Math.trunc(module$contents$jspb$utils_split64Low / module$contents$jspb$BinaryConstants_TWO_TO_32), module$contents$jspb$utils_split64High >>>= 0, module$contents$jspb$utils_split64Low >>>= 0);
      }
      if (b2) {
        const [d, e] = module$contents$jspb$utils_negate(module$contents$jspb$utils_split64Low, module$contents$jspb$utils_split64High);
        module$contents$jspb$utils_split64Low = d;
        module$contents$jspb$utils_split64High = e;
      }
    }
    function module$contents$jspb$utils_negate(a2, b2) {
      b2 = ~b2;
      a2 ? a2 = ~a2 + 1 : b2 += 1;
      return [a2, b2];
    }
    function module$contents$jspb$utils_countVarints(a2, b2, c) {
      let d = 0;
      for (let e = b2; e < c; e++) d += a2[e] >> 7;
      return c - b2 - d;
    }
    function module$contents$jspb$utils_countVarintFields(a2, b2, c, d) {
      let e = 0;
      d = 8 * d + module$contents$jspb$BinaryConstants_WireType.VARINT;
      if (128 > d) for (; b2 < c && a2[b2++] == d; ) for (e++; 0 != (a2[b2++] & 128); ) ;
      else for (; b2 < c; ) {
        let f = d;
        for (; 128 < f; ) {
          if (a2[b2] != (f & 127 | 128)) return e;
          b2++;
          f >>= 7;
        }
        if (a2[b2++] != f) break;
        for (e++; 0 != (a2[b2++] & 128); ) ;
      }
      return e;
    }
    function module$contents$jspb$utils_countFixedFields_(a2, b2, c, d, e) {
      let f = 0;
      if (128 > d) for (; b2 < c && a2[b2++] == d; ) f++, b2 += e;
      else for (; b2 < c; ) {
        let g = d;
        for (; 128 < g; ) {
          if (a2[b2++] != (g & 127 | 128)) return f;
          g >>= 7;
        }
        if (a2[b2++] != g) break;
        f++;
        b2 += e;
      }
      return f;
    }
    function module$contents$jspb$utils_countFixed32Fields(a2, b2, c, d) {
      return module$contents$jspb$utils_countFixedFields_(a2, b2, c, 8 * d + module$contents$jspb$BinaryConstants_WireType.FIXED32, 4);
    }
    function module$contents$jspb$utils_countFixed64Fields(a2, b2, c, d) {
      return module$contents$jspb$utils_countFixedFields_(a2, b2, c, 8 * d + module$contents$jspb$BinaryConstants_WireType.FIXED64, 8);
    }
    function module$contents$jspb$utils_countDelimitedFields(a2, b2, c, d) {
      let e = 0;
      for (d = 8 * d + module$contents$jspb$BinaryConstants_WireType.DELIMITED; b2 < c; ) {
        let f = d;
        for (; 128 < f; ) {
          if (a2[b2++] != (f & 127 | 128)) return e;
          f >>= 7;
        }
        if (a2[b2++] != f) break;
        e++;
        let g = 0, h = 1;
        for (; f = a2[b2++], g += (f & 127) * h, h *= 128, 0 != (f & 128); ) ;
        b2 += g;
      }
      return e;
    }
    function module$contents$jspb$utils_byteSourceToUint8Array(a2, b2) {
      if (a2.constructor === Uint8Array) return a2;
      if (a2.constructor === ArrayBuffer || a2.constructor === Array) return new Uint8Array(a2);
      if (a2.constructor === String) return (0, goog.crypt.base64.decodeStringToUint8Array)(a2);
      if (a2.constructor === module$contents$jspb$bytestring_ByteString) return b2 ? a2.asUint8Array() : module$contents$jspb$unsafe_bytestring_unsafeUint8ArrayFromByteString(a2);
      if (a2 instanceof Uint8Array) return new Uint8Array(a2.buffer, a2.byteOffset, a2.byteLength);
      throw Error("Type not convertible to a Uint8Array, expected a Uint8Array, an ArrayBuffer, a base64 encoded string, or Array of numbers");
    }
    function module$contents$jspb$utils_getSplit64Low() {
      return module$contents$jspb$utils_split64Low;
    }
    function module$contents$jspb$utils_getSplit64High() {
      return module$contents$jspb$utils_split64High;
    }
    function module$contents$jspb$utils_makeTag(a2, b2) {
      return 8 * a2 + b2;
    }
    var module$contents$jspb$utils_LOW_16_BITS = 65535;
    var module$contents$jspb$utils_LOW_24_BITS = 16777215;
    var module$contents$jspb$utils_ALL_32_BITS = 4294967295;
    var module$contents$jspb$utils_MAX_SAFE_INTEGER_DECIMAL_LENGTH = 16;
    jspb.utils.byteSourceToUint8Array = module$contents$jspb$utils_byteSourceToUint8Array;
    jspb.utils.countDelimitedFields = module$contents$jspb$utils_countDelimitedFields;
    jspb.utils.countFixed32Fields = module$contents$jspb$utils_countFixed32Fields;
    jspb.utils.countFixed64Fields = module$contents$jspb$utils_countFixed64Fields;
    jspb.utils.countVarintFields = module$contents$jspb$utils_countVarintFields;
    jspb.utils.countVarints = module$contents$jspb$utils_countVarints;
    jspb.utils.fromZigzag32 = module$contents$jspb$utils_fromZigzag32;
    jspb.utils.fromZigzag64 = module$contents$jspb$utils_fromZigzag64;
    jspb.utils.getSplit64High = module$contents$jspb$utils_getSplit64High;
    jspb.utils.getSplit64Low = module$contents$jspb$utils_getSplit64Low;
    jspb.utils.joinFloat32 = module$contents$jspb$utils_joinFloat32;
    jspb.utils.joinFloat64 = module$contents$jspb$utils_joinFloat64;
    jspb.utils.joinInt64 = module$contents$jspb$utils_joinInt64;
    jspb.utils.joinNegativeDecimalStringFallback = module$contents$jspb$utils_joinNegativeDecimalStringFallback;
    jspb.utils.joinSignedDecimalString = module$contents$jspb$utils_joinSignedDecimalString;
    jspb.utils.joinSignedNumberOrDecimalString = module$contents$jspb$utils_joinSignedNumberOrDecimalString;
    jspb.utils.joinUint64 = module$contents$jspb$utils_joinUint64;
    jspb.utils.joinUnsignedDecimalString = module$contents$jspb$utils_joinUnsignedDecimalString;
    jspb.utils.joinUnsignedDecimalStringFallback = module$contents$jspb$utils_joinUnsignedDecimalStringFallback;
    jspb.utils.joinUnsignedNumberOrDecimalString = module$contents$jspb$utils_joinUnsignedNumberOrDecimalString;
    jspb.utils.joinZigzag64 = module$contents$jspb$utils_joinZigzag64;
    jspb.utils.makeTag = module$contents$jspb$utils_makeTag;
    jspb.utils.sliceUint8Array = module$contents$jspb$utils_sliceUint8Array;
    jspb.utils.splitDecimalString = module$contents$jspb$utils_splitDecimalString;
    jspb.utils.splitDecimalStringFallback = module$contents$jspb$utils_splitDecimalStringFallback;
    jspb.utils.splitFloat32 = module$contents$jspb$utils_splitFloat32;
    jspb.utils.splitFloat64 = module$contents$jspb$utils_splitFloat64;
    jspb.utils.splitInt64 = module$contents$jspb$utils_splitInt64;
    jspb.utils.splitUint64 = module$contents$jspb$utils_splitUint64;
    jspb.utils.splitZigzag64 = module$contents$jspb$utils_splitZigzag64;
    jspb.utils.toZigzag32 = module$contents$jspb$utils_toZigzag32;
    jspb.utils.toZigzag64 = module$contents$jspb$utils_toZigzag64;
    var module$exports$jspb$binary$internal_buffer = { Buffer: class {
      constructor(a2, b2, c) {
        this.buffer = a2;
        if ((this.bufferAsByteStringInternal = c) && !b2) throw goog.DEBUG ? Error("Buffer must be immutable if a ByteString is provided.") : Error();
        this.isImmutable = b2;
      }
      getBufferAsByteStringIfImmutable() {
        if (!this.isImmutable) throw goog.DEBUG ? Error("Cannot get ByteString from mutable buffer.") : Error();
        return null == this.buffer ? null : this.bufferAsByteStringInternal ?? (this.bufferAsByteStringInternal = module$contents$jspb$unsafe_bytestring_unsafeByteStringFromUint8Array(this.buffer));
      }
    } };
    function module$contents$jspb$binary$internal_buffer_bufferFromSource(a2, b2) {
      if ("string" === typeof a2) return new module$exports$jspb$binary$internal_buffer.Buffer(module$contents$jspb$internal_bytes_decodeByteArray(a2), b2);
      if (Array.isArray(a2)) return new module$exports$jspb$binary$internal_buffer.Buffer(new Uint8Array(a2), b2);
      if (a2.constructor === Uint8Array) return new module$exports$jspb$binary$internal_buffer.Buffer(a2, false);
      if (a2.constructor === ArrayBuffer) return a2 = new Uint8Array(a2), new module$exports$jspb$binary$internal_buffer.Buffer(
        a2,
        false
      );
      if (a2.constructor === module$contents$jspb$bytestring_ByteString) return b2 = module$contents$jspb$unsafe_bytestring_unsafeUint8ArrayFromByteString(a2), new module$exports$jspb$binary$internal_buffer.Buffer(b2, true, a2);
      if (a2 instanceof Uint8Array) return a2 = a2.constructor === Uint8Array ? a2 : new Uint8Array(a2.buffer, a2.byteOffset, a2.byteLength), new module$exports$jspb$binary$internal_buffer.Buffer(a2, false);
      throw goog.DEBUG ? Error("Type not convertible to a Uint8Array, expected a Uint8Array, an ArrayBuffer, a base64 encoded string, a ByteString or an Array of numbers") : Error();
    }
    module$exports$jspb$binary$internal_buffer.bufferFromSource = module$contents$jspb$binary$internal_buffer_bufferFromSource;
    jspb.binary.decoder = {};
    var module$contents$jspb$binary$decoder_MAX_VARINT_SIZE = 10;
    var module$contents$jspb$binary$decoder_BinaryDecoder = class _module$contents$jspb$binary$decoder_BinaryDecoder {
      constructor(a2, b2, c, d) {
        this.buffer_ = this.bytes_ = null;
        this.bytesAreImmutable_ = false;
        module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST && (this.dataView_ = null);
        this.cursor_ = this.end_ = this.start_ = 0;
        this.init(a2, b2, c, d);
      }
      init(a2, b2, c, { aliasBytesFields: d = false, treatNewDataAsImmutable: e = false } = {}) {
        this.aliasBytesFields = d;
        this.treatNewDataAsImmutable = e;
        a2 && this.setBlock(a2, b2, c);
      }
      static alloc(a2, b2, c, d) {
        if (_module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_.length) {
          const e = _module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_.pop();
          e.init(a2, b2, c, d);
          return e;
        }
        return new _module$contents$jspb$binary$decoder_BinaryDecoder(a2, b2, c, d);
      }
      free() {
        this.clear();
        100 > _module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_.length && _module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_.push(this);
      }
      clear() {
        this.buffer_ = this.bytes_ = null;
        this.bytesAreImmutable_ = false;
        module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST && (this.dataView_ = null);
        this.cursor_ = this.end_ = this.start_ = 0;
        this.aliasBytesFields = false;
      }
      dataIsImmutable() {
        return this.bytesAreImmutable_;
      }
      getBuffer() {
        if (this.bytesAreImmutable_) throw goog.DEBUG ? Error("cannot access the buffer of decoders over immutable data.") : Error();
        return this.bytes_;
      }
      getBufferAsByteString() {
        if (null == this.buffer_) return null;
        if (!this.bytesAreImmutable_) throw goog.DEBUG ? Error("cannot access the buffer of decoders over immutable data.") : Error();
        return this.buffer_.getBufferAsByteStringIfImmutable();
      }
      setBlock(a2, b2, c) {
        this.buffer_ = a2 = module$contents$jspb$binary$internal_buffer_bufferFromSource(a2, this.treatNewDataAsImmutable);
        this.bytes_ = a2.buffer;
        this.bytesAreImmutable_ = a2.isImmutable;
        module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST && (this.dataView_ = null);
        this.start_ = b2 || 0;
        this.end_ = void 0 !== c ? this.start_ + c : this.bytes_.length;
        this.cursor_ = this.start_;
      }
      getEnd() {
        return this.end_;
      }
      setEnd(a2) {
        this.end_ = a2;
      }
      reset() {
        this.cursor_ = this.start_;
      }
      getCursor() {
        return this.cursor_;
      }
      setCursor(a2) {
        this.cursor_ = a2;
      }
      advance(a2) {
        this.setCursorAndCheck(this.cursor_ + a2);
      }
      atEnd() {
        return this.cursor_ == this.end_;
      }
      pastEnd() {
        return this.cursor_ > this.end_;
      }
      static readSplitVarint64(a2, b2) {
        let c, d = 0, e = 0, f = 0;
        const g = a2.bytes_;
        let h = a2.cursor_;
        do
          c = g[h++], d |= (c & 127) << f, f += 7;
        while (32 > f && c & 128);
        32 < f && (e |= (c & 127) >> 4);
        for (f = 3; 32 > f && c & 128; f += 7) c = g[h++], e |= (c & 127) << f;
        a2.setCursorAndCheck(h);
        if (128 > c) return b2(d >>> 0, e >>> 0);
        throw module$contents$jspb$binary$errors_invalidVarintError();
      }
      static readSplitZigzagVarint64(a2, b2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(
          a2,
          (c, d) => module$contents$jspb$utils_fromZigzag64(c, d, b2)
        );
      }
      static readSplitFixed64(a2, b2) {
        const c = a2.bytes_, d = a2.cursor_;
        a2.advance(8);
        let e = a2 = 0;
        for (let f = d + 7; f >= d; f--) a2 = a2 << 8 | c[f], e = e << 8 | c[f + 4];
        return b2(a2, e);
      }
      skipVarint() {
        _module$contents$jspb$binary$decoder_BinaryDecoder.readBool(this);
      }
      setCursorAndCheck(a2) {
        this.cursor_ = a2;
        if (a2 > this.end_) throw module$contents$jspb$binary$errors_readTooFarError(this.end_, a2);
      }
      static readSignedVarint32(a2) {
        const b2 = a2.bytes_;
        let c = a2.cursor_, d = b2[c++], e = d & 127;
        if (d & 128 && (d = b2[c++], e |= (d & 127) << 7, d & 128 && (d = b2[c++], e |= (d & 127) << 14, d & 128 && (d = b2[c++], e |= (d & 127) << 21, d & 128 && (d = b2[c++], e |= d << 28, d & 128 && b2[c++] & 128 && b2[c++] & 128 && b2[c++] & 128 && b2[c++] & 128 && b2[c++] & 128))))) throw module$contents$jspb$binary$errors_invalidVarintError();
        a2.setCursorAndCheck(c);
        return e;
      }
      static readUnsignedVarint32(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32(a2) >>> 0;
      }
      readUnsignedVarint32IfEqualTo(a2) {
        goog.asserts.assert(a2 === a2 >>> 0);
        const b2 = this.cursor_;
        let c = b2;
        const d = this.end_, e = this.bytes_;
        for (; c < d; ) if (127 < a2) {
          const f = 128 | a2 & 127;
          if (e[c++] !== f) break;
          a2 >>>= 7;
        } else {
          if (e[c++] === a2) return this.cursor_ = c, b2;
          break;
        }
        return -1;
      }
      static readZigzagVarint32(a2) {
        return module$contents$jspb$utils_fromZigzag32(_module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(a2));
      }
      static readUnsignedVarint64(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(a2, module$contents$jspb$utils_joinUint64);
      }
      static readUnsignedVarint64String(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(
          a2,
          module$contents$jspb$utils_joinUnsignedDecimalString
        );
      }
      static readSignedVarint64(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(a2, module$contents$jspb$utils_joinInt64);
      }
      static readSignedVarint64String(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(a2, module$contents$jspb$utils_joinSignedDecimalString);
      }
      static readZigzagVarint64(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(a2, module$contents$jspb$utils_joinZigzag64);
      }
      static readZigzagVarint64String(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSplitZigzagVarint64(
          a2,
          module$contents$jspb$utils_joinSignedDecimalString
        );
      }
      static readUint8(a2) {
        const b2 = a2.bytes_[a2.cursor_ + 0];
        a2.advance(1);
        return b2;
      }
      static readUint16(a2) {
        const b2 = a2.bytes_[a2.cursor_ + 0], c = a2.bytes_[a2.cursor_ + 1];
        a2.advance(2);
        return b2 << 0 | c << 8;
      }
      static readUint32(a2) {
        var b2 = a2.bytes_;
        const c = a2.cursor_, d = b2[c + 0], e = b2[c + 1], f = b2[c + 2];
        b2 = b2[c + 3];
        a2.advance(4);
        return (d << 0 | e << 8 | f << 16 | b2 << 24) >>> 0;
      }
      static readUint64(a2) {
        const b2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinUint64(b2, a2);
      }
      static readUint64String(a2) {
        const b2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinUnsignedDecimalString(b2, a2);
      }
      static readInt8(a2) {
        const b2 = a2.bytes_[a2.cursor_ + 0];
        a2.advance(1);
        return b2 << 24 >> 24;
      }
      static readInt16(a2) {
        const b2 = a2.bytes_[a2.cursor_ + 0], c = a2.bytes_[a2.cursor_ + 1];
        a2.advance(2);
        return (b2 << 0 | c << 8) << 16 >> 16;
      }
      static readInt32(a2) {
        var b2 = a2.bytes_;
        const c = a2.cursor_, d = b2[c + 0], e = b2[c + 1], f = b2[c + 2];
        b2 = b2[c + 3];
        a2.advance(4);
        return d << 0 | e << 8 | f << 16 | b2 << 24;
      }
      static readInt64(a2) {
        const b2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinInt64(b2, a2);
      }
      static readInt64String(a2) {
        const b2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinSignedDecimalString(
          b2,
          a2
        );
      }
      static readFloat(a2) {
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinFloat32(a2, 0);
      }
      static readDouble(a2) {
        if (module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST) {
          var b2 = a2.getDataView().getFloat64(a2.cursor_, true);
          a2.advance(8);
          return b2;
        }
        b2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        a2 = _module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(a2);
        return module$contents$jspb$utils_joinFloat64(b2, a2);
      }
      readDoubleArrayInto(a2, b2) {
        var c = this.cursor_, d = 8 * a2;
        if (c + d > this.end_) throw module$contents$jspb$binary$errors_readTooFarError(d, this.end_ - c);
        var e = this.bytes_;
        c += e.byteOffset;
        if (module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST) for (this.cursor_ += d, a2 = new DataView(e.buffer, c, d), d = 0; ; ) {
          e = d + 8;
          if (e > a2.byteLength) break;
          b2.push(a2.getFloat64(d, true));
          d = e;
        }
        else if (module$contents$jspb$binary$decoder_OPTIMIZE_LITTLE_ENDIAN_MACHINES && module$contents$jspb$binary$decoder_isLittleEndian()) for (this.cursor_ += d, a2 = new Float64Array(e.buffer.slice(
          c,
          c + d
        )), d = 0; d < a2.length; d++) b2.push(a2[d]);
        else for (d = 0; d < a2; d++) b2.push(_module$contents$jspb$binary$decoder_BinaryDecoder.readDouble(this));
      }
      static readBool(a2) {
        let b2 = 0, c = a2.cursor_;
        const d = c + module$contents$jspb$binary$decoder_MAX_VARINT_SIZE, e = a2.bytes_;
        for (; c < d; ) {
          const f = e[c++];
          b2 |= f;
          if (0 === (f & 128)) return a2.setCursorAndCheck(c), !!(b2 & 127);
        }
        throw module$contents$jspb$binary$errors_invalidVarintError();
      }
      static readEnum(a2) {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32(a2);
      }
      checkReadLengthAndAdvance(a2) {
        if (0 > a2) throw module$contents$jspb$binary$errors_negativeByteLengthError(a2);
        const b2 = this.cursor_, c = b2 + a2;
        if (c > this.end_) throw module$contents$jspb$binary$errors_readTooFarError(a2, this.end_ - b2);
        this.cursor_ = c;
        return b2;
      }
      readString(a2, b2) {
        const c = this.checkReadLengthAndAdvance(a2);
        return module$contents$jspb$binary$utf8_decodeUtf8(goog.asserts.assert(this.bytes_), c, a2, b2);
      }
      readBytes(a2) {
        const b2 = this.checkReadLengthAndAdvance(a2);
        return this.aliasBytesFields && !this.bytesAreImmutable_ ? this.bytes_.subarray(b2, b2 + a2) : module$contents$jspb$utils_sliceUint8Array(
          goog.asserts.assert(this.bytes_),
          b2,
          b2 + a2
        );
      }
      readByteString(a2) {
        if (0 == a2) return module$contents$jspb$bytestring_ByteString.empty();
        const b2 = this.checkReadLengthAndAdvance(a2);
        a2 = this.aliasBytesFields && this.bytesAreImmutable_ ? this.bytes_.subarray(b2, b2 + a2) : module$contents$jspb$utils_sliceUint8Array(goog.asserts.assert(this.bytes_), b2, b2 + a2);
        return module$contents$jspb$unsafe_bytestring_unsafeByteStringFromUint8Array(a2);
      }
      getDataView() {
        var a2 = this.dataView_;
        a2 || (a2 = this.bytes_, a2 = this.dataView_ = new DataView(a2.buffer, a2.byteOffset, a2.byteLength));
        return a2;
      }
      static resetInstanceCache() {
        _module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_ = [];
      }
      static getInstanceCache() {
        return _module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_;
      }
    };
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "getInstanceCache", module$contents$jspb$binary$decoder_BinaryDecoder.getInstanceCache);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "resetInstanceCache", module$contents$jspb$binary$decoder_BinaryDecoder.resetInstanceCache);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "readByteString", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.readByteString);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "readBytes", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.readBytes);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "readString", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.readString);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readEnum", module$contents$jspb$binary$decoder_BinaryDecoder.readEnum);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readBool", module$contents$jspb$binary$decoder_BinaryDecoder.readBool);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "readDoubleArrayInto", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.readDoubleArrayInto);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readDouble", module$contents$jspb$binary$decoder_BinaryDecoder.readDouble);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readFloat", module$contents$jspb$binary$decoder_BinaryDecoder.readFloat);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readInt64String", module$contents$jspb$binary$decoder_BinaryDecoder.readInt64String);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readInt64", module$contents$jspb$binary$decoder_BinaryDecoder.readInt64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readInt32", module$contents$jspb$binary$decoder_BinaryDecoder.readInt32);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readInt16", module$contents$jspb$binary$decoder_BinaryDecoder.readInt16);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readInt8", module$contents$jspb$binary$decoder_BinaryDecoder.readInt8);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUint64String", module$contents$jspb$binary$decoder_BinaryDecoder.readUint64String);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUint64", module$contents$jspb$binary$decoder_BinaryDecoder.readUint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUint32", module$contents$jspb$binary$decoder_BinaryDecoder.readUint32);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUint16", module$contents$jspb$binary$decoder_BinaryDecoder.readUint16);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUint8", module$contents$jspb$binary$decoder_BinaryDecoder.readUint8);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readZigzagVarint64String", module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64String);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readZigzagVarint64", module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSignedVarint64String", module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64String);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSignedVarint64", module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUnsignedVarint64String", module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64String);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUnsignedVarint64", module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readZigzagVarint32", module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint32);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "readUnsignedVarint32IfEqualTo", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.readUnsignedVarint32IfEqualTo);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readUnsignedVarint32", module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSignedVarint32", module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "skipVarint", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.skipVarint);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSplitFixed64", module$contents$jspb$binary$decoder_BinaryDecoder.readSplitFixed64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSplitZigzagVarint64", module$contents$jspb$binary$decoder_BinaryDecoder.readSplitZigzagVarint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "readSplitVarint64", module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "pastEnd", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.pastEnd);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "atEnd", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.atEnd);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "advance", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.advance);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "setCursor", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.setCursor);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "getCursor", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.getCursor);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "reset", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.reset);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "setEnd", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.setEnd);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "getEnd", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.getEnd);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "setBlock", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.setBlock);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "getBufferAsByteString", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.getBufferAsByteString);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "getBuffer", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.getBuffer);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "dataIsImmutable", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.dataIsImmutable);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "clear", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.clear);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder.prototype, "free", module$contents$jspb$binary$decoder_BinaryDecoder.prototype.free);
    goog.exportProperty(module$contents$jspb$binary$decoder_BinaryDecoder, "alloc", module$contents$jspb$binary$decoder_BinaryDecoder.alloc);
    module$contents$jspb$binary$decoder_BinaryDecoder.instanceCache_ = [];
    function module$contents$jspb$binary$decoder_isLittleEndian() {
      void 0 === module$contents$jspb$binary$decoder_isLittleEndianCache && (module$contents$jspb$binary$decoder_isLittleEndianCache = 513 == new Uint16Array(new Uint8Array([1, 2]).buffer)[0]);
      return goog.asserts.assertBoolean(module$contents$jspb$binary$decoder_isLittleEndianCache);
    }
    var module$contents$jspb$binary$decoder_isLittleEndianCache = void 0;
    var module$contents$jspb$binary$decoder_ASSUME_DATAVIEW_IS_FAST = 2019 <= goog.FEATURESET_YEAR;
    var module$contents$jspb$binary$decoder_OPTIMIZE_LITTLE_ENDIAN_MACHINES = true;
    jspb.binary.decoder.BinaryDecoder = module$contents$jspb$binary$decoder_BinaryDecoder;
    jspb.binary.reader = {};
    var module$contents$jspb$binary$reader_ENFORCE_UTF8 = "ALWAYS";
    goog.asserts.assert("DEPRECATED_PROTO3_ONLY" === module$contents$jspb$binary$reader_ENFORCE_UTF8 || "ALWAYS" === module$contents$jspb$binary$reader_ENFORCE_UTF8);
    var module$contents$jspb$binary$reader_UTF8_PARSING_ERRORS_ARE_FATAL = "ALWAYS" === module$contents$jspb$binary$reader_ENFORCE_UTF8;
    var module$contents$jspb$binary$reader_BinaryReaderOptions = class {
      constructor() {
      }
    };
    var module$contents$jspb$binary$reader_BinaryReader = class _module$contents$jspb$binary$reader_BinaryReader {
      constructor(a2, b2, c, d) {
        this.decoder_ = module$contents$jspb$binary$decoder_BinaryDecoder.alloc(a2, b2, c, d);
        this.fieldCursor_ = this.decoder_.getCursor();
        this.nextField_ = module$contents$jspb$BinaryConstants_INVALID_FIELD_NUMBER;
        this.nextTag_ = module$contents$jspb$BinaryConstants_INVALID_TAG;
        this.nextWireType_ = module$contents$jspb$BinaryConstants_WireType.INVALID;
        this.setOptions(d);
      }
      setOptions({ discardUnknownFields: a2 = false } = {}) {
        this.discardUnknownFields = a2;
      }
      static alloc(a2, b2, c, d) {
        if (_module$contents$jspb$binary$reader_BinaryReader.instanceCache_.length) {
          const e = _module$contents$jspb$binary$reader_BinaryReader.instanceCache_.pop();
          e.setOptions(d);
          e.decoder_.init(a2, b2, c, d);
          return e;
        }
        return new _module$contents$jspb$binary$reader_BinaryReader(a2, b2, c, d);
      }
      free() {
        this.decoder_.clear();
        this.nextTag_ = module$contents$jspb$BinaryConstants_INVALID_TAG;
        this.nextField_ = module$contents$jspb$BinaryConstants_INVALID_FIELD_NUMBER;
        this.nextWireType_ = module$contents$jspb$BinaryConstants_WireType.INVALID;
        100 > _module$contents$jspb$binary$reader_BinaryReader.instanceCache_.length && _module$contents$jspb$binary$reader_BinaryReader.instanceCache_.push(this);
      }
      getFieldCursor() {
        return this.fieldCursor_;
      }
      getCursor() {
        return this.decoder_.getCursor();
      }
      dataIsImmutable() {
        return this.decoder_.dataIsImmutable();
      }
      getBuffer() {
        return this.decoder_.getBuffer();
      }
      getBufferAsByteString() {
        return this.decoder_.getBufferAsByteString();
      }
      getTag() {
        return this.nextTag_;
      }
      getFieldNumber() {
        return this.nextField_;
      }
      getWireType() {
        return this.nextWireType_;
      }
      isEndGroup() {
        return this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.END_GROUP;
      }
      isDelimited() {
        return this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED;
      }
      reset() {
        this.decoder_.reset();
        this.fieldCursor_ = this.decoder_.getCursor();
        this.nextTag_ = module$contents$jspb$BinaryConstants_INVALID_TAG;
        this.nextField_ = module$contents$jspb$BinaryConstants_INVALID_FIELD_NUMBER;
        this.nextWireType_ = module$contents$jspb$BinaryConstants_WireType.INVALID;
      }
      advance(a2) {
        this.decoder_.advance(a2);
      }
      nextField() {
        if (this.decoder_.atEnd()) return false;
        this.assertPriorFieldWasRead();
        this.fieldCursor_ = this.decoder_.getCursor();
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_), b2 = module$contents$jspb$binary$reader_parseFieldNumber(a2), c = module$contents$jspb$binary$reader_parseWireType(a2);
        if (!module$contents$jspb$BinaryConstants_isValidWireType(c)) throw module$contents$jspb$binary$errors_invalidWireTypeError(c, this.fieldCursor_);
        if (1 > b2) throw module$contents$jspb$binary$errors_invalidFieldNumberError(b2, this.fieldCursor_);
        this.nextTag_ = a2;
        this.nextField_ = b2;
        this.nextWireType_ = c;
        return true;
      }
      nextFieldIfTagEqualTo(a2) {
        this.assertPriorFieldWasRead();
        goog.asserts.assert(module$contents$jspb$BinaryConstants_isValidWireType(module$contents$jspb$binary$reader_parseWireType(a2)) && 0 < module$contents$jspb$binary$reader_parseFieldNumber(a2), "Must pass a valid tag.");
        const b2 = this.decoder_.readUnsignedVarint32IfEqualTo(a2), c = 0 <= b2;
        c && (this.fieldCursor_ = b2, this.nextTag_ = a2, this.nextField_ = module$contents$jspb$binary$reader_parseFieldNumber(a2), this.nextWireType_ = module$contents$jspb$binary$reader_parseWireType(a2));
        return c;
      }
      assertPriorFieldWasRead() {
        if (goog.asserts.ENABLE_ASSERTS && this.nextTag_ !== module$contents$jspb$BinaryConstants_INVALID_TAG) {
          const a2 = this.decoder_.getCursor();
          this.decoder_.setCursor(this.fieldCursor_);
          module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
          this.nextWireType_ === module$contents$jspb$BinaryConstants_WireType.END_GROUP || this.nextWireType_ === module$contents$jspb$BinaryConstants_WireType.START_GROUP ? goog.asserts.assert(a2 === this.decoder_.getCursor(), "Expected to not advance the cursor.  Group tags do not have values.") : goog.asserts.assert(a2 > this.decoder_.getCursor(), "Expected to read the field, did you forget to call a read or skip method?");
          this.decoder_.setCursor(a2);
        }
      }
      skipVarintField() {
        this.nextWireType_ != module$contents$jspb$BinaryConstants_WireType.VARINT ? (goog.asserts.fail("Invalid wire type for skipVarintField"), this.skipField()) : this.decoder_.skipVarint();
      }
      skipDelimitedField() {
        if (this.nextWireType_ != module$contents$jspb$BinaryConstants_WireType.DELIMITED) return goog.asserts.fail("Invalid wire type for skipDelimitedField"), this.skipField(), 0;
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
        this.decoder_.advance(a2);
        return a2;
      }
      skipFixed32Field() {
        goog.asserts.assert(this.nextWireType_ === module$contents$jspb$BinaryConstants_WireType.FIXED32);
        this.decoder_.advance(4);
      }
      skipFixed64Field() {
        goog.asserts.assert(this.nextWireType_ === module$contents$jspb$BinaryConstants_WireType.FIXED64);
        this.decoder_.advance(8);
      }
      skipGroup() {
        const a2 = this.nextField_;
        do {
          if (!this.nextField()) throw module$contents$jspb$binary$errors_unmatchedStartGroupEofError();
          if (this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.END_GROUP) {
            if (this.nextField_ != a2) throw module$contents$jspb$binary$errors_unmatchedStartGroupError();
            break;
          }
          this.skipField();
        } while (1);
      }
      skipField() {
        switch (this.nextWireType_) {
          case module$contents$jspb$BinaryConstants_WireType.VARINT:
            this.skipVarintField();
            break;
          case module$contents$jspb$BinaryConstants_WireType.FIXED64:
            this.skipFixed64Field();
            break;
          case module$contents$jspb$BinaryConstants_WireType.DELIMITED:
            this.skipDelimitedField();
            break;
          case module$contents$jspb$BinaryConstants_WireType.FIXED32:
            this.skipFixed32Field();
            break;
          case module$contents$jspb$BinaryConstants_WireType.START_GROUP:
            this.skipGroup();
            break;
          default:
            throw module$contents$jspb$binary$errors_invalidWireTypeError(this.nextWireType_, this.fieldCursor_);
        }
      }
      skipToEnd() {
        this.decoder_.setCursor(this.decoder_.getEnd());
      }
      readUnknownField() {
        const a2 = this.getFieldCursor();
        this.skipField();
        return this.readUnknownFieldsStartingFrom(a2);
      }
      readUnknownFieldsStartingFrom(a2) {
        if (!this.discardUnknownFields) {
          const b2 = this.decoder_.getCursor(), c = b2 - a2;
          this.decoder_.setCursor(a2);
          a2 = this.decoder_.readByteString(c);
          goog.asserts.assert(b2 == this.decoder_.getCursor());
          return a2;
        }
      }
      readAny(a2) {
        if (module$contents$jspb$BinaryConstants_FieldTypeToWireType(a2) !== this.nextWireType_) return null;
        const b2 = module$contents$jspb$BinaryConstants_FieldType;
        switch (a2) {
          case b2.DOUBLE:
            return this.readDouble();
          case b2.FLOAT:
            return this.readFloat();
          case b2.INT64:
            return this.readInt64();
          case b2.UINT64:
            return this.readUint64();
          case b2.INT32:
            return this.readInt32();
          case b2.FIXED64:
            return this.readFixed64();
          case b2.FIXED32:
            return this.readFixed32();
          case b2.BOOL:
            return this.readBool();
          case b2.STRING:
            return this.readString();
          case b2.GROUP:
            goog.asserts.fail("Group field type not supported in readAny()");
          case b2.MESSAGE:
            goog.asserts.fail("Message field type not supported in readAny()");
          case b2.BYTES:
            return this.readBytes();
          case b2.UINT32:
            return this.readUint32();
          case b2.ENUM:
            return this.readEnum();
          case b2.SFIXED32:
            return this.readSfixed32();
          case b2.SFIXED64:
            return this.readSfixed64();
          case b2.SINT32:
            return this.readSint32();
          case b2.SINT64:
            return this.readSint64();
          default:
            goog.asserts.fail("Invalid field type in readAny()");
        }
        return null;
      }
      readMessage(a2, b2, c, d, e) {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        const f = this.decoder_.getEnd(), g = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_), h = this.decoder_.getCursor() + g;
        let l = h - f;
        0 >= l && (this.decoder_.setEnd(h), b2(a2, this, c, d, e), l = h - this.decoder_.getCursor());
        if (l) throw module$contents$jspb$binary$errors_messageLengthMismatchError(g, g - l);
        this.decoder_.setCursor(h);
        this.decoder_.setEnd(f);
        return a2;
      }
      readGroup(a2, b2, c) {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.START_GROUP);
        goog.asserts.assert(this.nextField_ == a2);
        c(b2, this);
        if (this.nextWireType_ !== module$contents$jspb$BinaryConstants_WireType.END_GROUP) throw module$contents$jspb$binary$errors_groupDidNotEndWithEndGroupError();
        if (this.nextField_ !== a2) throw module$contents$jspb$binary$errors_unmatchedStartGroupError();
        return b2;
      }
      isMessageSetGroup() {
        return this.getTag() === module$contents$jspb$binary$reader_MESSAGE_SET_START_GROUP_TAG;
      }
      readMessageSetGroup(a2) {
        goog.asserts.assert(this.isMessageSetGroup());
        let b2 = 0, c = 0;
        for (; this.nextField() && !this.isEndGroup(); ) this.getTag() !== module$contents$jspb$binary$reader_MESSAGE_SET_TYPE_ID_TAG || b2 ? this.getTag() !== module$contents$jspb$binary$reader_MESSAGE_SET_MESSAGE_TAG || c ? this.skipField() : b2 ? (c = -1, this.readMessage(b2, a2)) : (c = this.getFieldCursor(), this.skipDelimitedField()) : (b2 = this.readUint32(), c && (goog.asserts.assert(0 < c), goog.asserts.ENABLE_ASSERTS && (this.nextTag_ = module$contents$jspb$BinaryConstants_INVALID_TAG, this.nextWireType_ = module$contents$jspb$BinaryConstants_WireType.INVALID), this.decoder_.setCursor(c), c = 0));
        if (this.getTag() !== module$contents$jspb$binary$reader_MESSAGE_SET_END_TAG || !c || !b2) throw module$contents$jspb$binary$errors_malformedBinaryBytesForMessageSet();
      }
      readInt32() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32(this.decoder_);
      }
      readInt64() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64(this.decoder_);
      }
      readInt64String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64String(this.decoder_);
      }
      readUint32() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
      }
      readUint64() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64(this.decoder_);
      }
      readUint64String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64String(this.decoder_);
      }
      readSint32() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint32(this.decoder_);
      }
      readSint64() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64(this.decoder_);
      }
      readSint64String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64String(this.decoder_);
      }
      readFixed32() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED32);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUint32(this.decoder_);
      }
      readFixed64() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUint64(this.decoder_);
      }
      readFixed64String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUint64String(this.decoder_);
      }
      readSfixed32() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED32);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readInt32(this.decoder_);
      }
      readSfixed32String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED32);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readInt32(this.decoder_).toString();
      }
      readSfixed64() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readInt64(this.decoder_);
      }
      readSfixed64String() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readInt64String(this.decoder_);
      }
      readFloat() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED32);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readFloat(this.decoder_);
      }
      readDouble() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readDouble(this.decoder_);
      }
      readBool() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readBool(this.decoder_);
      }
      readEnum() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32(this.decoder_);
      }
      readString() {
        if (module$contents$jspb$binary$reader_UTF8_PARSING_ERRORS_ARE_FATAL) return this.readStringRequireUtf8();
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
        return this.decoder_.readString(a2, false);
      }
      readStringRequireUtf8() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
        return this.decoder_.readString(a2, true);
      }
      readBytes() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
        return this.decoder_.readBytes(a2);
      }
      readByteString() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        const a2 = module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
        return this.decoder_.readByteString(a2);
      }
      readSplitVarint64(a2) {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(
          this.decoder_,
          a2
        );
      }
      readSplitZigzagVarint64(a2) {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.VARINT);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSplitVarint64(this.decoder_, (b2, c) => module$contents$jspb$utils_fromZigzag64(b2, c, a2));
      }
      readSplitFixed64(a2) {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.FIXED64);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readSplitFixed64(this.decoder_, a2);
      }
      readPackedFieldInto_(a2, b2) {
        var c = this.readPackedFieldLength_();
        for (c = this.decoder_.getCursor() + c; this.decoder_.getCursor() < c; ) b2.push(a2(this.decoder_));
      }
      readPackedFieldLength_() {
        goog.asserts.assert(this.nextWireType_ == module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        return module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32(this.decoder_);
      }
      readPackableInt32Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint32, a2) : a2.push(this.readInt32());
      }
      readPackableInt64Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64, a2) : a2.push(this.readInt64());
      }
      readPackableInt64StringInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readSignedVarint64String, a2) : a2.push(this.readInt64String());
      }
      readPackableUint32Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint32, a2) : a2.push(this.readUint32());
      }
      readPackableUint64Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64, a2) : a2.push(this.readUint64());
      }
      readPackableUint64StringInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUnsignedVarint64String, a2) : a2.push(this.readUint64String());
      }
      readPackableSint32Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint32, a2) : a2.push(this.readSint32());
      }
      readPackableSint64Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64, a2) : a2.push(this.readSint64());
      }
      readPackableSint64StringInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readZigzagVarint64String, a2) : a2.push(this.readSint64String());
      }
      readPackableFixed32Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUint32, a2) : a2.push(this.readFixed32());
      }
      readPackableFixed64Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUint64, a2) : a2.push(this.readFixed64());
      }
      readPackableFixed64StringInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readUint64String, a2) : a2.push(this.readFixed64String());
      }
      readPackableSfixed32Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readInt32, a2) : a2.push(this.readSfixed32());
      }
      readPackableSfixed64Into(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readInt64, a2) : a2.push(this.readSfixed64());
      }
      readPackableSfixed64StringInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readInt64String, a2) : a2.push(this.readSfixed64String());
      }
      readPackedFixed32() {
        const a2 = [];
        this.readPackableFixed32Into(a2);
        return a2;
      }
      readPackedFixed64() {
        const a2 = [];
        this.readPackableFixed64Into(a2);
        return a2;
      }
      readPackedFixed64String() {
        const a2 = [];
        this.readPackableFixed64StringInto(a2);
        return a2;
      }
      readPackedSfixed32() {
        const a2 = [];
        this.readPackableSfixed32Into(a2);
        return a2;
      }
      readPackedSfixed64String() {
        const a2 = [];
        this.readPackableSfixed64StringInto(a2);
        return a2;
      }
      readPackableFloatInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readFloat, a2) : a2.push(this.readFloat());
      }
      readPackableDoubleInto(a2) {
        this.isDelimited() ? this.decoder_.readDoubleArrayInto(this.readPackedFieldLength_() / 8, a2) : a2.push(this.readDouble());
      }
      readPackableBoolInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readBool, a2) : a2.push(this.readBool());
      }
      readPackableEnumInto(a2) {
        this.isDelimited() ? this.readPackedFieldInto_(module$contents$jspb$binary$decoder_BinaryDecoder.readEnum, a2) : a2.push(this.readEnum());
      }
      static resetInstanceCache() {
        _module$contents$jspb$binary$reader_BinaryReader.instanceCache_ = [];
      }
      static getInstanceCache() {
        return _module$contents$jspb$binary$reader_BinaryReader.instanceCache_;
      }
    };
    goog.exportProperty(module$contents$jspb$binary$reader_BinaryReader.prototype, "readPackedSfixed64String", module$contents$jspb$binary$reader_BinaryReader.prototype.readPackedSfixed64String);
    goog.exportProperty(module$contents$jspb$binary$reader_BinaryReader.prototype, "readPackedSfixed32", module$contents$jspb$binary$reader_BinaryReader.prototype.readPackedSfixed32);
    goog.exportProperty(module$contents$jspb$binary$reader_BinaryReader.prototype, "readPackedFixed64String", module$contents$jspb$binary$reader_BinaryReader.prototype.readPackedFixed64String);
    goog.exportProperty(module$contents$jspb$binary$reader_BinaryReader.prototype, "readPackedFixed64", module$contents$jspb$binary$reader_BinaryReader.prototype.readPackedFixed64);
    goog.exportProperty(module$contents$jspb$binary$reader_BinaryReader.prototype, "readPackedFixed32", module$contents$jspb$binary$reader_BinaryReader.prototype.readPackedFixed32);
    function module$contents$jspb$binary$reader_parseWireType(a2) {
      return a2 & 7;
    }
    function module$contents$jspb$binary$reader_parseFieldNumber(a2) {
      return a2 >>> 3;
    }
    module$contents$jspb$binary$reader_BinaryReader.instanceCache_ = [];
    var module$contents$jspb$binary$reader_MESSAGE_SET_START_GROUP_TAG = module$contents$jspb$utils_makeTag(module$contents$jspb$BinaryConstants_MESSAGE_SET_GROUP_NUMBER, module$contents$jspb$BinaryConstants_WireType.START_GROUP);
    var module$contents$jspb$binary$reader_MESSAGE_SET_TYPE_ID_TAG = module$contents$jspb$utils_makeTag(module$contents$jspb$BinaryConstants_MESSAGE_SET_TYPE_ID_FIELD_NUMBER, module$contents$jspb$BinaryConstants_WireType.VARINT);
    var module$contents$jspb$binary$reader_MESSAGE_SET_MESSAGE_TAG = module$contents$jspb$utils_makeTag(module$contents$jspb$BinaryConstants_MESSAGE_SET_MESSAGE_FIELD_NUMBER, module$contents$jspb$BinaryConstants_WireType.DELIMITED);
    var module$contents$jspb$binary$reader_MESSAGE_SET_END_TAG = module$contents$jspb$utils_makeTag(module$contents$jspb$BinaryConstants_MESSAGE_SET_GROUP_NUMBER, module$contents$jspb$BinaryConstants_WireType.END_GROUP);
    jspb.binary.reader.BinaryReader = module$contents$jspb$binary$reader_BinaryReader;
    jspb.binary.reader.BinaryReaderOptions = module$contents$jspb$binary$reader_BinaryReaderOptions;
    jspb.binary.reader.UTF8_PARSING_ERRORS_ARE_FATAL = module$contents$jspb$binary$reader_UTF8_PARSING_ERRORS_ARE_FATAL;
    var module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo = function(a2, b2, c, d, e) {
      this.fieldIndex = a2;
      this.fieldName = b2;
      this.ctor = c;
      this.toObjectFn = d;
      this.isRepeated = e;
    };
    module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo.prototype.isMessageType = function() {
      return !!this.ctor;
    };
    goog.exportProperty(module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo.prototype, "isMessageType", module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo.prototype.isMessageType);
    jspb.ExtensionFieldInfo = module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo;
    var module$contents$jspb$ExtensionFieldBinaryInfo_ExtensionFieldBinaryInfo = function(a2, b2, c, d, e, f) {
      this.fieldInfo = a2;
      this.binaryReaderFn = b2;
      this.binaryWriterFn = c;
      this.binaryMessageSerializeFn = d;
      this.binaryMessageDeserializeFn = e;
      this.isPacked = f;
    };
    jspb.ExtensionFieldBinaryInfo = module$contents$jspb$ExtensionFieldBinaryInfo_ExtensionFieldBinaryInfo;
    var module$contents$jspb$Message_Message = function() {
    };
    module$contents$jspb$Message_Message.GENERATE_TO_OBJECT = true;
    goog.exportSymbol("module$contents$jspb$Message_Message.GENERATE_TO_OBJECT", module$contents$jspb$Message_Message.GENERATE_TO_OBJECT);
    module$contents$jspb$Message_Message.GENERATE_FROM_OBJECT = !goog.DISALLOW_TEST_ONLY_CODE;
    goog.exportSymbol("module$contents$jspb$Message_Message.GENERATE_FROM_OBJECT", module$contents$jspb$Message_Message.GENERATE_FROM_OBJECT);
    module$contents$jspb$Message_Message.GENERATE_TO_STRING = true;
    module$contents$jspb$Message_Message.ASSUME_LOCAL_ARRAYS = false;
    module$contents$jspb$Message_Message.SERIALIZE_EMPTY_TRAILING_FIELDS = true;
    module$contents$jspb$Message_Message.SUPPORTS_UINT8ARRAY_ = "function" == typeof Uint8Array;
    module$contents$jspb$Message_Message.prototype.getJsPbMessageId = function() {
      return this.messageId_;
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "getJsPbMessageId", module$contents$jspb$Message_Message.prototype.getJsPbMessageId);
    module$contents$jspb$Message_Message.getIndex_ = function(a2, b2) {
      return b2 + a2.arrayIndexOffset_;
    };
    module$contents$jspb$Message_Message.hiddenES6Property_ = class {
    };
    module$contents$jspb$Message_Message.getFieldNumber_ = function(a2, b2) {
      return b2 - a2.arrayIndexOffset_;
    };
    module$contents$jspb$Message_Message.initialize = function(a2, b2, c, d, e, f) {
      a2.wrappers_ = null;
      b2 || (b2 = c ? [c] : []);
      a2.messageId_ = c ? String(c) : void 0;
      a2.arrayIndexOffset_ = 0 === c ? -1 : 0;
      a2.array = b2;
      module$contents$jspb$Message_Message.initPivotAndExtensionObject_(a2, d);
      a2.convertedPrimitiveFields_ = {};
      module$contents$jspb$Message_Message.SERIALIZE_EMPTY_TRAILING_FIELDS || (a2.repeatedFields = e);
      if (e) for (b2 = 0; b2 < e.length; b2++) c = e[b2], c < a2.pivot_ ? (c = module$contents$jspb$Message_Message.getIndex_(a2, c), a2.array[c] = a2.array[c] || module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_) : (module$contents$jspb$Message_Message.maybeInitEmptyExtensionObject_(a2), a2.extensionObject_[c] = a2.extensionObject_[c] || module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_);
      if (f && f.length) for (b2 = 0; b2 < f.length; b2++) module$contents$jspb$Message_Message.computeOneofCase(a2, f[b2]);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.initialize", module$contents$jspb$Message_Message.initialize);
    module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_ = goog.DEBUG && Object.freeze ? Object.freeze([]) : [];
    module$contents$jspb$Message_Message.isArray_ = function(a2) {
      return module$contents$jspb$Message_Message.ASSUME_LOCAL_ARRAYS ? a2 instanceof Array : Array.isArray(a2);
    };
    module$contents$jspb$Message_Message.isExtensionObject_ = function(a2) {
      return null !== a2 && "object" == typeof a2 && !module$contents$jspb$Message_Message.isArray_(a2) && !(module$contents$jspb$Message_Message.SUPPORTS_UINT8ARRAY_ && a2 instanceof Uint8Array);
    };
    module$contents$jspb$Message_Message.initPivotAndExtensionObject_ = function(a2, b2) {
      var c = a2.array.length, d = -1;
      if (c && (d = c - 1, c = a2.array[d], module$contents$jspb$Message_Message.isExtensionObject_(c))) {
        a2.pivot_ = module$contents$jspb$Message_Message.getFieldNumber_(a2, d);
        a2.extensionObject_ = c;
        return;
      }
      -1 < b2 ? (a2.pivot_ = Math.max(b2, module$contents$jspb$Message_Message.getFieldNumber_(a2, d + 1)), a2.extensionObject_ = null) : a2.pivot_ = Number.MAX_VALUE;
    };
    module$contents$jspb$Message_Message.maybeInitEmptyExtensionObject_ = function(a2) {
      var b2 = module$contents$jspb$Message_Message.getIndex_(a2, a2.pivot_);
      a2.array[b2] || (a2.extensionObject_ = a2.array[b2] = {});
    };
    module$contents$jspb$Message_Message.toObjectList = function(a2, b2, c) {
      for (var d = [], e = 0; e < a2.length; e++) d[e] = b2.call(a2[e], c, a2[e]);
      return d;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.toObjectList", module$contents$jspb$Message_Message.toObjectList);
    module$contents$jspb$Message_Message.toObjectExtension = function(a2, b2, c, d, e) {
      for (var f in c) {
        var g = c[f], h = d.call(a2, g);
        if (null != h) {
          for (var l in g.fieldName) if (g.fieldName.hasOwnProperty(l)) break;
          b2[l] = g.toObjectFn ? g.isRepeated ? module$contents$jspb$Message_Message.toObjectList(h, g.toObjectFn, e) : g.toObjectFn(e, h) : h;
        }
      }
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.toObjectExtension", module$contents$jspb$Message_Message.toObjectExtension);
    module$contents$jspb$Message_Message.serializeBinaryExtensions = function(a2, b2, c, d) {
      for (var e in c) {
        var f = c[e], g = f.fieldInfo;
        if (!f.binaryWriterFn) throw Error("Message extension present that was generated without binary serialization support");
        var h = d.call(a2, g);
        if (null != h) if (g.isMessageType()) if (f.binaryMessageSerializeFn) f.binaryWriterFn.call(b2, g.fieldIndex, h, f.binaryMessageSerializeFn);
        else throw Error("Message extension present holding submessage without binary support enabled, and message is being serialized to binary format");
        else f.binaryWriterFn.call(b2, g.fieldIndex, h);
      }
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.serializeBinaryExtensions", module$contents$jspb$Message_Message.serializeBinaryExtensions);
    module$contents$jspb$Message_Message.readBinaryExtension = function(a2, b2, c, d, e) {
      var f = c[b2.getFieldNumber()];
      if (f) {
        c = f.fieldInfo;
        if (!f.binaryReaderFn) throw Error("Deserializing extension whose generated code does not support binary format");
        if (c.isMessageType()) {
          var g = new c.ctor();
          f.binaryReaderFn.call(b2, g, f.binaryMessageDeserializeFn);
        } else {
          if (c.isRepeated && f.isPacked) {
            g = d.call(a2, c) ?? [];
            f.binaryReaderFn.call(b2, g);
            e.call(a2, c, g);
            return;
          }
          g = f.binaryReaderFn.call(b2);
        }
        c.isRepeated && !f.isPacked ? (b2 = d.call(a2, c)) ? b2.push(g) : e.call(a2, c, [g]) : e.call(a2, c, g);
      } else b2.skipField();
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.readBinaryExtension", module$contents$jspb$Message_Message.readBinaryExtension);
    module$contents$jspb$Message_Message.getField = function(a2, b2) {
      if (b2 < a2.pivot_) {
        b2 = module$contents$jspb$Message_Message.getIndex_(a2, b2);
        var c = a2.array[b2];
        return c === module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_ ? a2.array[b2] = [] : c;
      }
      if (a2.extensionObject_) return c = a2.extensionObject_[b2], c === module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_ ? a2.extensionObject_[b2] = [] : c;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getField", module$contents$jspb$Message_Message.getField);
    module$contents$jspb$Message_Message.getRepeatedField = function(a2, b2) {
      return module$contents$jspb$Message_Message.getField(a2, b2);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getRepeatedField", module$contents$jspb$Message_Message.getRepeatedField);
    module$contents$jspb$Message_Message.getOptionalFloatingPointField = function(a2, b2) {
      a2 = module$contents$jspb$Message_Message.getField(a2, b2);
      return null == a2 ? a2 : +a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getOptionalFloatingPointField", module$contents$jspb$Message_Message.getOptionalFloatingPointField);
    module$contents$jspb$Message_Message.getBooleanField = function(a2, b2) {
      a2 = module$contents$jspb$Message_Message.getField(a2, b2);
      return null == a2 ? a2 : !!a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getBooleanField", module$contents$jspb$Message_Message.getBooleanField);
    module$contents$jspb$Message_Message.getRepeatedFloatingPointField = function(a2, b2) {
      var c = module$contents$jspb$Message_Message.getRepeatedField(a2, b2);
      a2.convertedPrimitiveFields_ || (a2.convertedPrimitiveFields_ = {});
      if (!a2.convertedPrimitiveFields_[b2]) {
        for (var d = 0; d < c.length; d++) c[d] = +c[d];
        a2.convertedPrimitiveFields_[b2] = true;
      }
      return c;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getRepeatedFloatingPointField", module$contents$jspb$Message_Message.getRepeatedFloatingPointField);
    module$contents$jspb$Message_Message.getRepeatedBooleanField = function(a2, b2) {
      var c = module$contents$jspb$Message_Message.getRepeatedField(a2, b2);
      a2.convertedPrimitiveFields_ || (a2.convertedPrimitiveFields_ = {});
      if (!a2.convertedPrimitiveFields_[b2]) {
        for (var d = 0; d < c.length; d++) c[d] = !!c[d];
        a2.convertedPrimitiveFields_[b2] = true;
      }
      return c;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getRepeatedBooleanField", module$contents$jspb$Message_Message.getRepeatedBooleanField);
    module$contents$jspb$Message_Message.bytesAsB64 = function(a2) {
      if (null == a2 || "string" === typeof a2) return a2;
      if (module$contents$jspb$Message_Message.SUPPORTS_UINT8ARRAY_ && a2 instanceof Uint8Array) return goog.crypt.base64.encodeByteArray(a2);
      module$contents$jspb$asserts_fail("Cannot coerce to b64 string: " + goog.typeOf(a2));
      return null;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.bytesAsB64", module$contents$jspb$Message_Message.bytesAsB64);
    module$contents$jspb$Message_Message.bytesAsU8 = function(a2) {
      if (null == a2 || a2 instanceof Uint8Array) return a2;
      if ("string" === typeof a2) return goog.crypt.base64.decodeStringToUint8Array(a2);
      module$contents$jspb$asserts_fail("Cannot coerce to Uint8Array: " + goog.typeOf(a2));
      return null;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.bytesAsU8", module$contents$jspb$Message_Message.bytesAsU8);
    module$contents$jspb$Message_Message.bytesListAsB64 = function(a2) {
      module$contents$jspb$Message_Message.assertConsistentTypes_(a2);
      return a2.length && "string" !== typeof a2[0] ? module$contents$goog$array_map(a2, module$contents$jspb$Message_Message.bytesAsB64) : a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.bytesListAsB64", module$contents$jspb$Message_Message.bytesListAsB64);
    module$contents$jspb$Message_Message.bytesListAsU8 = function(a2) {
      module$contents$jspb$Message_Message.assertConsistentTypes_(a2);
      return !a2.length || a2[0] instanceof Uint8Array ? a2 : module$contents$goog$array_map(a2, module$contents$jspb$Message_Message.bytesAsU8);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.bytesListAsU8", module$contents$jspb$Message_Message.bytesListAsU8);
    module$contents$jspb$Message_Message.assertConsistentTypes_ = function(a2) {
      if (goog.DEBUG && a2 && 1 < a2.length) {
        var b2 = goog.typeOf(a2[0]);
        module$contents$goog$array_forEach(a2, function(c) {
          goog.typeOf(c) != b2 && module$contents$jspb$asserts_fail("Inconsistent type in JSPB repeated field array. Got " + goog.typeOf(c) + " expected " + b2);
        });
      }
    };
    module$contents$jspb$Message_Message.getFieldWithDefault = function(a2, b2, c) {
      a2 = module$contents$jspb$Message_Message.getField(a2, b2);
      return null == a2 ? c : a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getFieldWithDefault", module$contents$jspb$Message_Message.getFieldWithDefault);
    module$contents$jspb$Message_Message.getBooleanFieldWithDefault = function(a2, b2, c) {
      a2 = module$contents$jspb$Message_Message.getBooleanField(a2, b2);
      return null == a2 ? c : a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getBooleanFieldWithDefault", module$contents$jspb$Message_Message.getBooleanFieldWithDefault);
    module$contents$jspb$Message_Message.getFloatingPointFieldWithDefault = function(a2, b2, c) {
      a2 = module$contents$jspb$Message_Message.getOptionalFloatingPointField(a2, b2);
      return null == a2 ? c : a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getFloatingPointFieldWithDefault", module$contents$jspb$Message_Message.getFloatingPointFieldWithDefault);
    module$contents$jspb$Message_Message.getFieldProto3 = module$contents$jspb$Message_Message.getFieldWithDefault;
    goog.exportSymbol("module$contents$jspb$Message_Message.getFieldProto3", module$contents$jspb$Message_Message.getFieldProto3);
    module$contents$jspb$Message_Message.getMapField = function(a2, b2, c, d) {
      a2.wrappers_ || (a2.wrappers_ = {});
      if (b2 in a2.wrappers_) return a2.wrappers_[b2];
      var e = module$contents$jspb$Message_Message.getField(a2, b2);
      if (!e) {
        if (c) return;
        e = [];
        module$contents$jspb$Message_Message.setField(a2, b2, e);
      }
      return a2.wrappers_[b2] = new module$contents$jspb$Map_Map(e, d);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getMapField", module$contents$jspb$Message_Message.getMapField);
    module$contents$jspb$Message_Message.setField = function(a2, b2, c) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      b2 < a2.pivot_ ? a2.array[module$contents$jspb$Message_Message.getIndex_(a2, b2)] = c : (module$contents$jspb$Message_Message.maybeInitEmptyExtensionObject_(a2), a2.extensionObject_[b2] = c);
      return a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setField", module$contents$jspb$Message_Message.setField);
    module$contents$jspb$Message_Message.setProto3IntField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, 0);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3IntField", module$contents$jspb$Message_Message.setProto3IntField);
    module$contents$jspb$Message_Message.setProto3FloatField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, 0);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3FloatField", module$contents$jspb$Message_Message.setProto3FloatField);
    module$contents$jspb$Message_Message.setProto3BooleanField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, false);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3BooleanField", module$contents$jspb$Message_Message.setProto3BooleanField);
    module$contents$jspb$Message_Message.setProto3StringField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, "");
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3StringField", module$contents$jspb$Message_Message.setProto3StringField);
    module$contents$jspb$Message_Message.setProto3BytesField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, "");
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3BytesField", module$contents$jspb$Message_Message.setProto3BytesField);
    module$contents$jspb$Message_Message.setProto3EnumField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, 0);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3EnumField", module$contents$jspb$Message_Message.setProto3EnumField);
    module$contents$jspb$Message_Message.setProto3StringIntField = function(a2, b2, c) {
      return module$contents$jspb$Message_Message.setFieldIgnoringDefault_(a2, b2, c, "0");
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setProto3StringIntField", module$contents$jspb$Message_Message.setProto3StringIntField);
    module$contents$jspb$Message_Message.setFieldIgnoringDefault_ = function(a2, b2, c, d) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      c !== d ? module$contents$jspb$Message_Message.setField(a2, b2, c) : b2 < a2.pivot_ ? a2.array[module$contents$jspb$Message_Message.getIndex_(a2, b2)] = null : (module$contents$jspb$Message_Message.maybeInitEmptyExtensionObject_(a2), delete a2.extensionObject_[b2]);
      return a2;
    };
    module$contents$jspb$Message_Message.addToRepeatedField = function(a2, b2, c, d) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      b2 = module$contents$jspb$Message_Message.getRepeatedField(a2, b2);
      void 0 != d ? b2.splice(d, 0, c) : b2.push(c);
      return a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.addToRepeatedField", module$contents$jspb$Message_Message.addToRepeatedField);
    module$contents$jspb$Message_Message.setOneofField = function(a2, b2, c, d) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      (c = module$contents$jspb$Message_Message.computeOneofCase(a2, c)) && c !== b2 && void 0 !== d && (a2.wrappers_ && c in a2.wrappers_ && (a2.wrappers_[c] = void 0), module$contents$jspb$Message_Message.setField(a2, c, void 0));
      return module$contents$jspb$Message_Message.setField(a2, b2, d);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setOneofField", module$contents$jspb$Message_Message.setOneofField);
    module$contents$jspb$Message_Message.computeOneofCase = function(a2, b2) {
      for (var c, d, e = 0; e < b2.length; e++) {
        var f = b2[e], g = module$contents$jspb$Message_Message.getField(a2, f);
        null != g && (c = f, d = g, module$contents$jspb$Message_Message.setField(a2, f, void 0));
      }
      return c ? (module$contents$jspb$Message_Message.setField(a2, c, d), c) : 0;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.computeOneofCase", module$contents$jspb$Message_Message.computeOneofCase);
    module$contents$jspb$Message_Message.getWrapperField = function(a2, b2, c, d) {
      a2.wrappers_ || (a2.wrappers_ = {});
      if (!a2.wrappers_[c]) {
        var e = module$contents$jspb$Message_Message.getField(a2, c);
        if (d || e) a2.wrappers_[c] = new b2(e);
      }
      return a2.wrappers_[c];
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getWrapperField", module$contents$jspb$Message_Message.getWrapperField);
    module$contents$jspb$Message_Message.getRepeatedWrapperField = function(a2, b2, c) {
      module$contents$jspb$Message_Message.wrapRepeatedField_(a2, b2, c);
      b2 = a2.wrappers_[c];
      b2 == module$contents$jspb$Message_Message.EMPTY_LIST_SENTINEL_ && (b2 = a2.wrappers_[c] = []);
      return b2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.getRepeatedWrapperField", module$contents$jspb$Message_Message.getRepeatedWrapperField);
    module$contents$jspb$Message_Message.wrapRepeatedField_ = function(a2, b2, c) {
      a2.wrappers_ || (a2.wrappers_ = {});
      if (!a2.wrappers_[c]) {
        for (var d = module$contents$jspb$Message_Message.getRepeatedField(a2, c), e = [], f = 0; f < d.length; f++) e[f] = new b2(d[f]);
        a2.wrappers_[c] = e;
      }
    };
    module$contents$jspb$Message_Message.setWrapperField = function(a2, b2, c) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      a2.wrappers_ || (a2.wrappers_ = {});
      var d = c ? c.toArray() : c;
      a2.wrappers_[b2] = c;
      return module$contents$jspb$Message_Message.setField(a2, b2, d);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setWrapperField", module$contents$jspb$Message_Message.setWrapperField);
    module$contents$jspb$Message_Message.setOneofWrapperField = function(a2, b2, c, d) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      a2.wrappers_ || (a2.wrappers_ = {});
      var e = d ? d.toArray() : d;
      a2.wrappers_[b2] = d;
      return module$contents$jspb$Message_Message.setOneofField(a2, b2, c, e);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setOneofWrapperField", module$contents$jspb$Message_Message.setOneofWrapperField);
    module$contents$jspb$Message_Message.setRepeatedWrapperField = function(a2, b2, c) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      a2.wrappers_ || (a2.wrappers_ = {});
      c = c || [];
      for (var d = [], e = 0; e < c.length; e++) d[e] = c[e].toArray();
      a2.wrappers_[b2] = c;
      return module$contents$jspb$Message_Message.setField(a2, b2, d);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.setRepeatedWrapperField", module$contents$jspb$Message_Message.setRepeatedWrapperField);
    module$contents$jspb$Message_Message.addToRepeatedWrapperField = function(a2, b2, c, d, e) {
      module$contents$jspb$Message_Message.wrapRepeatedField_(a2, d, b2);
      var f = a2.wrappers_[b2];
      f || (f = a2.wrappers_[b2] = []);
      c = c ? c : new d();
      a2 = module$contents$jspb$Message_Message.getRepeatedField(a2, b2);
      void 0 != e ? (f.splice(e, 0, c), a2.splice(e, 0, c.toArray())) : (f.push(c), a2.push(c.toArray()));
      return c;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.addToRepeatedWrapperField", module$contents$jspb$Message_Message.addToRepeatedWrapperField);
    module$contents$jspb$Message_Message.toMap = function(a2, b2, c, d) {
      for (var e = {}, f = 0; f < a2.length; f++) e[b2.call(a2[f])] = c ? c.call(a2[f], d, a2[f]) : a2[f];
      return e;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.toMap", module$contents$jspb$Message_Message.toMap);
    module$contents$jspb$Message_Message.prototype.syncMapFields_ = function() {
      if (this.wrappers_) for (var a2 in this.wrappers_) {
        var b2 = this.wrappers_[a2];
        if (Array.isArray(b2)) for (var c = 0; c < b2.length; c++) b2[c] && b2[c].toArray();
        else b2 && b2.toArray();
      }
    };
    module$contents$jspb$Message_Message.prototype.toArray = function() {
      this.syncMapFields_();
      return this.array;
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "toArray", module$contents$jspb$Message_Message.prototype.toArray);
    module$contents$jspb$Message_Message.GENERATE_TO_STRING && (module$contents$jspb$Message_Message.prototype.toString = function() {
      this.syncMapFields_();
      return this.array.toString();
    });
    module$contents$jspb$Message_Message.prototype.getExtension = function(a2) {
      if (this.extensionObject_) {
        this.wrappers_ || (this.wrappers_ = {});
        var b2 = a2.fieldIndex;
        if (a2.isRepeated) {
          if (a2.isMessageType()) return this.wrappers_[b2] || (this.wrappers_[b2] = module$contents$goog$array_map(this.extensionObject_[b2] || [], function(c) {
            return new a2.ctor(c);
          })), this.wrappers_[b2];
        } else if (a2.isMessageType()) return !this.wrappers_[b2] && this.extensionObject_[b2] && (this.wrappers_[b2] = new a2.ctor(this.extensionObject_[b2])), this.wrappers_[b2];
        return this.extensionObject_[b2];
      }
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "getExtension", module$contents$jspb$Message_Message.prototype.getExtension);
    module$contents$jspb$Message_Message.prototype.setExtension = function(a2, b2) {
      this.wrappers_ || (this.wrappers_ = {});
      module$contents$jspb$Message_Message.maybeInitEmptyExtensionObject_(this);
      var c = a2.fieldIndex;
      a2.isRepeated ? (b2 = b2 || [], a2.isMessageType() ? (this.wrappers_[c] = b2, this.extensionObject_[c] = module$contents$goog$array_map(b2, function(d) {
        return d.toArray();
      })) : this.extensionObject_[c] = b2) : a2.isMessageType() ? (this.wrappers_[c] = b2, this.extensionObject_[c] = b2 ? b2.toArray() : b2) : this.extensionObject_[c] = b2;
      return this;
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "setExtension", module$contents$jspb$Message_Message.prototype.setExtension);
    module$contents$jspb$Message_Message.difference = function(a2, b2) {
      if (!(a2 instanceof b2.constructor)) throw Error("Messages have different types.");
      var c = a2.toArray();
      b2 = b2.toArray();
      var d = [], e = 0, f = c.length > b2.length ? c.length : b2.length;
      a2.getJsPbMessageId() && (d[0] = a2.getJsPbMessageId(), e = 1);
      for (; e < f; e++) module$contents$jspb$Message_Message.compareFields(c[e], b2[e]) || (d[e] = b2[e]);
      return new a2.constructor(d);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.difference", module$contents$jspb$Message_Message.difference);
    module$contents$jspb$Message_Message.equals = function(a2, b2) {
      return a2 == b2 || !(!a2 || !b2) && a2 instanceof b2.constructor && module$contents$jspb$Message_Message.compareFields(a2.toArray(), b2.toArray());
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.equals", module$contents$jspb$Message_Message.equals);
    module$contents$jspb$Message_Message.compareExtensions = function(a2, b2) {
      a2 = a2 || {};
      b2 = b2 || {};
      var c = {}, d;
      for (d in a2) c[d] = 0;
      for (d in b2) c[d] = 0;
      for (d in c) if (!module$contents$jspb$Message_Message.compareFields(a2[d], b2[d])) return false;
      return true;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.compareExtensions", module$contents$jspb$Message_Message.compareExtensions);
    module$contents$jspb$Message_Message.compareFields = function(a2, b2) {
      if (a2 == b2) return true;
      if (!goog.isObject(a2) || !goog.isObject(b2)) return "number" === typeof a2 && isNaN(a2) || "number" === typeof b2 && isNaN(b2) ? String(a2) == String(b2) : false;
      if (a2.constructor != b2.constructor) return false;
      if (module$contents$jspb$Message_Message.SUPPORTS_UINT8ARRAY_ && a2.constructor === Uint8Array) {
        if (a2.length != b2.length) return false;
        for (var c = 0; c < a2.length; c++) if (a2[c] != b2[c]) return false;
        return true;
      }
      if (a2.constructor === Array) {
        var d = void 0, e = void 0, f = Math.max(
          a2.length,
          b2.length
        );
        for (c = 0; c < f; c++) {
          var g = a2[c], h = b2[c];
          g && g.constructor == Object && (module$contents$jspb$asserts_assert(void 0 === d), module$contents$jspb$asserts_assert(c === a2.length - 1), d = g, g = void 0);
          h && h.constructor == Object && (module$contents$jspb$asserts_assert(void 0 === e), module$contents$jspb$asserts_assert(c === b2.length - 1), e = h, h = void 0);
          if (!module$contents$jspb$Message_Message.compareFields(g, h)) return false;
        }
        return d || e ? (d = d || {}, e = e || {}, module$contents$jspb$Message_Message.compareExtensions(d, e)) : true;
      }
      if (a2.constructor === Object) return module$contents$jspb$Message_Message.compareExtensions(a2, b2);
      throw Error("Invalid type in JSPB array");
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.compareFields", module$contents$jspb$Message_Message.compareFields);
    module$contents$jspb$Message_Message.prototype.cloneMessage = function() {
      return module$contents$jspb$Message_Message.cloneMessage(this);
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "cloneMessage", module$contents$jspb$Message_Message.prototype.cloneMessage);
    module$contents$jspb$Message_Message.prototype.clone = function() {
      return module$contents$jspb$Message_Message.cloneMessage(this);
    };
    goog.exportProperty(module$contents$jspb$Message_Message.prototype, "clone", module$contents$jspb$Message_Message.prototype.clone);
    module$contents$jspb$Message_Message.clone = function(a2) {
      return module$contents$jspb$Message_Message.cloneMessage(a2);
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.clone", module$contents$jspb$Message_Message.clone);
    module$contents$jspb$Message_Message.cloneMessage = function(a2) {
      return new a2.constructor(module$contents$jspb$Message_Message.clone_(a2.toArray()));
    };
    module$contents$jspb$Message_Message.copyInto = function(a2, b2) {
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message);
      module$contents$jspb$asserts_assertInstanceof(b2, module$contents$jspb$Message_Message);
      module$contents$jspb$asserts_assert(a2.constructor == b2.constructor, "Copy source and target message should have the same type.");
      a2 = module$contents$jspb$Message_Message.clone(a2);
      for (var c = b2.toArray(), d = a2.toArray(), e = c.length = 0; e < d.length; e++) c[e] = d[e];
      b2.wrappers_ = a2.wrappers_;
      b2.extensionObject_ = a2.extensionObject_;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.copyInto", module$contents$jspb$Message_Message.copyInto);
    module$contents$jspb$Message_Message.clone_ = function(a2) {
      if (Array.isArray(a2)) {
        for (var b2 = Array(a2.length), c = 0; c < a2.length; c++) {
          var d = a2[c];
          null != d && (b2[c] = "object" == typeof d ? module$contents$jspb$Message_Message.clone_(module$contents$jspb$asserts_assert(d)) : d);
        }
        return b2;
      }
      if (module$contents$jspb$Message_Message.SUPPORTS_UINT8ARRAY_ && a2 instanceof Uint8Array) return new Uint8Array(a2);
      b2 = {};
      for (c in a2) d = a2[c], null != d && (b2[c] = "object" == typeof d ? module$contents$jspb$Message_Message.clone_(module$contents$jspb$asserts_assert(d)) : d);
      return b2;
    };
    module$contents$jspb$Message_Message.registerMessageType = function(a2, b2) {
      b2.messageId = a2;
    };
    goog.exportSymbol("module$contents$jspb$Message_Message.registerMessageType", module$contents$jspb$Message_Message.registerMessageType);
    module$contents$jspb$Message_Message.messageSetExtensions = {};
    module$contents$jspb$Message_Message.messageSetExtensionsBinary = {};
    jspb.Message = module$contents$jspb$Message_Message;
    jspb.debug = {};
    function module$contents$jspb$debug_dump(a2) {
      if (!goog.DEBUG) return null;
      module$contents$jspb$asserts_assertInstanceof(a2, module$contents$jspb$Message_Message, "jspb.Message instance expected");
      module$contents$jspb$asserts_assert(a2.getExtension, "Only unobfuscated and unoptimized compilation modes supported.");
      return module$contents$jspb$debug_dump_(a2);
    }
    function module$contents$jspb$debug_dump_(a2) {
      var b2 = goog.typeOf(a2);
      if ("number" == b2 || "string" == b2 || "boolean" == b2 || "null" == b2 || "undefined" == b2 || "undefined" !== typeof Uint8Array && a2 instanceof Uint8Array) return a2;
      if ("array" == b2) return module$contents$jspb$asserts_assertArray(a2), module$contents$goog$array_map(a2, module$contents$jspb$debug_dump_);
      if (a2 instanceof module$contents$jspb$Map_Map) {
        var c = {};
        a2 = a2.entries();
        for (var d = a2.next(); !d.done; d = a2.next()) c[d.value[0]] = module$contents$jspb$debug_dump_(d.value[1]);
        return c;
      }
      module$contents$jspb$asserts_assertInstanceof(
        a2,
        module$contents$jspb$Message_Message,
        "Only messages expected: " + a2
      );
      b2 = a2.constructor;
      var e = { $name: b2.name || b2.displayName };
      for (h in b2.prototype) {
        var f = /^get([A-Z]\w*)/.exec(h);
        if (f && "getExtension" != h && "getJsPbMessageId" != h) {
          var g = "has" + f[1];
          if (!a2[g] || a2[g]()) g = a2[h](), e[module$contents$jspb$debug_formatFieldName_(f[1])] = module$contents$jspb$debug_dump_(g);
        }
      }
      if (COMPILED && a2.extensionObject_) return e.$extensions = "Recursive dumping of extensions not supported in compiled code. Switch to uncompiled or dump extension object directly", e;
      for (d in b2.extensions) if (/^\d+$/.test(d)) {
        f = b2.extensions[d];
        var h = a2.getExtension(f);
        f = module$contents$goog$object_getKeys(f.fieldName)[0];
        null != h && (c || (c = e.$extensions = {}), c[module$contents$jspb$debug_formatFieldName_(f)] = module$contents$jspb$debug_dump_(h));
      }
      return e;
    }
    function module$contents$jspb$debug_formatFieldName_(a2) {
      return a2.replace(/^[A-Z]/, function(b2) {
        return b2.toLowerCase();
      });
    }
    jspb.debug.dump = module$contents$jspb$debug_dump;
    jspb.BinaryReader = module$contents$jspb$binary$reader_BinaryReader;
    jspb.binary.encoder = {};
    var module$contents$jspb$binary$encoder_MAX_PUSH = 8192;
    var module$contents$jspb$binary$encoder_BinaryEncoder = class {
      constructor() {
        this.buffer_ = [];
      }
      length() {
        return this.buffer_.length;
      }
      end() {
        const a2 = this.buffer_;
        this.buffer_ = [];
        return a2;
      }
      writeSplitVarint64(a2, b2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(b2 == Math.floor(b2));
        goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_32);
        for (goog.asserts.assert(0 <= b2 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_32); 0 < b2 || 127 < a2; ) this.buffer_.push(a2 & 127 | 128), a2 = (a2 >>> 7 | b2 << 25) >>> 0, b2 >>>= 7;
        this.buffer_.push(a2);
      }
      writeSplitFixed64(a2, b2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(b2 == Math.floor(b2));
        goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_32);
        goog.asserts.assert(0 <= b2 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_32);
        this.writeUint32(a2);
        this.writeUint32(b2);
      }
      writeSplitZigzagVarint64(a2, b2) {
        module$contents$jspb$utils_toZigzag64(a2, b2, (c, d) => {
          this.writeSplitVarint64(c >>> 0, d >>> 0);
        });
      }
      writeUnsignedVarint32(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        for (goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_32); 127 < a2; ) this.buffer_.push(a2 & 127 | 128), a2 >>>= 7;
        this.buffer_.push(a2);
      }
      writeSignedVarint32(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_31);
        if (0 <= a2) this.writeUnsignedVarint32(a2);
        else {
          for (let b2 = 0; 9 > b2; b2++) this.buffer_.push(a2 & 127 | 128), a2 >>= 7;
          this.buffer_.push(1);
        }
      }
      writeUnsignedVarint64(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_64);
        module$contents$jspb$utils_splitInt64(a2);
        this.writeSplitVarint64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High());
      }
      writeSignedVarint64(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_63 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_63);
        module$contents$jspb$utils_splitInt64(a2);
        this.writeSplitVarint64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High());
      }
      writeZigzagVarint32(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_31);
        this.writeUnsignedVarint32(module$contents$jspb$utils_toZigzag32(a2));
      }
      writeZigzagVarint64(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_63 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_63);
        module$contents$jspb$utils_splitZigzag64(a2);
        this.writeSplitVarint64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High());
      }
      writeZigzagVarint64String(a2) {
        module$contents$jspb$utils_splitDecimalString(a2);
        module$contents$jspb$utils_toZigzag64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High(), (b2, c) => {
          this.writeSplitVarint64(b2 >>> 0, c >>> 0);
        });
      }
      writeUint8(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(0 <= a2 && 256 > a2);
        this.buffer_.push(a2 >>> 0 & 255);
      }
      writeUint16(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(0 <= a2 && 65536 > a2);
        this.buffer_.push(a2 >>> 0 & 255);
        this.buffer_.push(a2 >>> 8 & 255);
      }
      writeUint32(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_32);
        this.buffer_.push(a2 >>> 0 & 255);
        this.buffer_.push(a2 >>> 8 & 255);
        this.buffer_.push(a2 >>> 16 & 255);
        this.buffer_.push(a2 >>> 24 & 255);
      }
      writeUint64(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(0 <= a2 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_64);
        module$contents$jspb$utils_splitUint64(a2);
        this.writeUint32(module$contents$jspb$utils_getSplit64Low());
        this.writeUint32(module$contents$jspb$utils_getSplit64High());
      }
      writeInt8(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(-128 <= a2 && 128 > a2);
        this.buffer_.push(a2 >>> 0 & 255);
      }
      writeInt16(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(-32768 <= a2 && 32768 > a2);
        this.buffer_.push(a2 >>> 0 & 255);
        this.buffer_.push(a2 >>> 8 & 255);
      }
      writeInt32(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_31);
        this.buffer_.push(a2 >>> 0 & 255);
        this.buffer_.push(a2 >>> 8 & 255);
        this.buffer_.push(a2 >>> 16 & 255);
        this.buffer_.push(a2 >>> 24 & 255);
      }
      writeInt64(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_63 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_63);
        module$contents$jspb$utils_splitInt64(a2);
        this.writeSplitFixed64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High());
      }
      writeFloat(a2) {
        goog.asserts.assert(Infinity == a2 || -Infinity == a2 || isNaN(a2) || "number" === typeof a2 && a2 >= -module$contents$jspb$BinaryConstants_FLOAT32_MAX && a2 <= module$contents$jspb$BinaryConstants_FLOAT32_MAX);
        module$contents$jspb$utils_splitFloat32(a2);
        this.writeUint32(module$contents$jspb$utils_getSplit64Low());
      }
      writeDouble(a2) {
        goog.asserts.assert("number" === typeof a2 || "Infinity" === a2 || "-Infinity" === a2 || "NaN" === a2);
        module$contents$jspb$utils_splitFloat64(a2);
        this.writeUint32(module$contents$jspb$utils_getSplit64Low());
        this.writeUint32(module$contents$jspb$utils_getSplit64High());
      }
      writeBool(a2) {
        goog.asserts.assert("boolean" === typeof a2 || "number" === typeof a2);
        this.buffer_.push(a2 ? 1 : 0);
      }
      writeEnum(a2) {
        goog.asserts.assert(a2 == Math.floor(a2));
        goog.asserts.assert(a2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && a2 < module$contents$jspb$BinaryConstants_TWO_TO_31);
        this.writeSignedVarint32(a2);
      }
      writeBytes(a2) {
        for (; a2.length > module$contents$jspb$binary$encoder_MAX_PUSH; ) Array.prototype.push.apply(this.buffer_, a2.subarray(0, module$contents$jspb$binary$encoder_MAX_PUSH)), a2 = a2.subarray(module$contents$jspb$binary$encoder_MAX_PUSH);
        Array.prototype.push.apply(this.buffer_, a2);
      }
    };
    jspb.binary.encoder.BinaryEncoder = module$contents$jspb$binary$encoder_BinaryEncoder;
    jspb.arith = {};
    var module$contents$jspb$arith_UInt64 = class _module$contents$jspb$arith_UInt64 {
      constructor(a2, b2) {
        this.lo = a2 >>> 0;
        this.hi = b2 >>> 0;
      }
      toDecimalString() {
        return module$contents$jspb$utils_joinUnsignedDecimalString(this.lo, this.hi);
      }
      negateInTwosComplement() {
        return 0 === this.lo ? new _module$contents$jspb$arith_UInt64(0, 1 + ~this.hi) : new _module$contents$jspb$arith_UInt64(~this.lo + 1, ~this.hi);
      }
      static fromBigInt(a2) {
        a2 = BigInt.asUintN(64, a2);
        return new _module$contents$jspb$arith_UInt64(Number(a2 & BigInt(4294967295)), Number(a2 >> BigInt(32)));
      }
      static fromString(a2) {
        if (!a2) return _module$contents$jspb$arith_UInt64.getZero();
        if (!/^\d+$/.test(a2)) return null;
        module$contents$jspb$utils_splitDecimalString(a2);
        return new _module$contents$jspb$arith_UInt64(module$contents$jspb$utils_getSplit64Low(), module$contents$jspb$utils_getSplit64High());
      }
      static fromNumber(a2) {
        return new _module$contents$jspb$arith_UInt64(a2 & module$contents$jspb$arith_ALL_32_BITS, a2 / module$contents$jspb$arith_TWO_PWR_32_DBL);
      }
      static getZero() {
        return module$contents$jspb$arith_uint64Zero || (module$contents$jspb$arith_uint64Zero = new _module$contents$jspb$arith_UInt64(0, 0));
      }
    };
    var module$contents$jspb$arith_uint64Zero;
    var module$contents$jspb$arith_Int64 = class _module$contents$jspb$arith_Int64 {
      constructor(a2, b2) {
        this.lo = a2 >>> 0;
        this.hi = b2 >>> 0;
      }
      toDecimalString() {
        return module$contents$jspb$utils_joinSignedDecimalString(this.lo, this.hi);
      }
      static fromBigInt(a2) {
        a2 = BigInt.asUintN(64, a2);
        return new _module$contents$jspb$arith_Int64(Number(a2 & BigInt(4294967295)), Number(a2 >> BigInt(32)));
      }
      static fromString(a2) {
        if (!a2) return _module$contents$jspb$arith_Int64.getZero();
        if (!/^-?\d+$/.test(a2)) return null;
        module$contents$jspb$utils_splitDecimalString(a2);
        return new _module$contents$jspb$arith_Int64(
          module$contents$jspb$utils_getSplit64Low(),
          module$contents$jspb$utils_getSplit64High()
        );
      }
      static fromNumber(a2) {
        return new _module$contents$jspb$arith_Int64(a2 & module$contents$jspb$arith_ALL_32_BITS, a2 / module$contents$jspb$arith_TWO_PWR_32_DBL);
      }
      static getZero() {
        return module$contents$jspb$arith_int64Zero || (module$contents$jspb$arith_int64Zero = new _module$contents$jspb$arith_Int64(0, 0));
      }
    };
    var module$contents$jspb$arith_int64Zero;
    var module$contents$jspb$arith_ALL_32_BITS = 4294967295;
    var module$contents$jspb$arith_TWO_PWR_32_DBL = 4294967296;
    jspb.arith.UInt64 = module$contents$jspb$arith_UInt64;
    jspb.arith.Int64 = module$contents$jspb$arith_Int64;
    jspb.binary.writer = {};
    var module$contents$jspb$binary$writer_REJECT_UNPAIRED_SURROGATES = goog.DEBUG;
    var module$contents$jspb$binary$writer_BinaryWriter = class {
      constructor() {
        this.blocks_ = [];
        this.totalLength_ = 0;
        this.encoder_ = new module$contents$jspb$binary$encoder_BinaryEncoder();
      }
      pushBlock(a2) {
        0 !== a2.length && (this.blocks_.push(a2), this.totalLength_ += a2.length);
      }
      appendUint8Array_(a2) {
        this.pushBlock(this.encoder_.end());
        this.pushBlock(a2);
      }
      beginDelimited_(a2) {
        this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        a2 = this.encoder_.end();
        this.pushBlock(a2);
        a2.push(this.totalLength_);
        return a2;
      }
      endDelimited_(a2) {
        var b2 = a2.pop();
        b2 = this.totalLength_ + this.encoder_.length() - b2;
        for ((0, goog.asserts.assert)(0 <= b2); 127 < b2; ) a2.push(b2 & 127 | 128), b2 >>>= 7, this.totalLength_++;
        a2.push(b2);
        this.totalLength_++;
      }
      writeUnknownFields(a2) {
        this.pushBlock(this.encoder_.end());
        for (let b2 = 0; b2 < a2.length; b2++) this.pushBlock(module$contents$jspb$unsafe_bytestring_unsafeUint8ArrayFromByteString(a2[b2]));
      }
      writeSerializedMessage(a2, b2, c) {
        this.appendUint8Array_(a2.subarray(b2, c));
      }
      maybeWriteSerializedMessage(a2, b2, c) {
        null != a2 && null != b2 && null != c && this.writeSerializedMessage(
          a2,
          b2,
          c
        );
      }
      reset() {
        this.blocks_ = [];
        this.encoder_.end();
        this.totalLength_ = 0;
      }
      getResultBuffer() {
        this.pushBlock(this.encoder_.end());
        const a2 = new Uint8Array(this.totalLength_), b2 = this.blocks_, c = b2.length;
        let d = 0;
        for (let e = 0; e < c; e++) {
          const f = b2[e];
          a2.set(f, d);
          d += f.length;
        }
        (0, goog.asserts.assert)(d == a2.length);
        this.blocks_ = [a2];
        return a2;
      }
      getResultBufferAsByteString() {
        return module$contents$jspb$unsafe_bytestring_unsafeByteStringFromUint8Array(this.getResultBuffer());
      }
      getResultBase64String(a2) {
        return void 0 === a2 ? module$contents$jspb$internal_bytes_encodeByteArray(this.getResultBuffer()) : (0, goog.crypt.base64.encodeByteArray)(this.getResultBuffer(), a2);
      }
      writeFieldHeader_(a2, b2) {
        (0, goog.asserts.assert)(1 <= a2 && a2 == Math.floor(a2));
        this.encoder_.writeUnsignedVarint32(module$contents$jspb$utils_makeTag(a2, b2));
      }
      writeAny(a2, b2, c) {
        switch (a2) {
          case module$contents$jspb$BinaryConstants_FieldType.DOUBLE:
            this.writeDouble(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.FLOAT:
            this.writeFloat(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.INT64:
            this.writeInt64(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.UINT64:
            this.writeUint64(
              b2,
              c
            );
            break;
          case module$contents$jspb$BinaryConstants_FieldType.INT32:
            this.writeInt32(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.FIXED64:
            this.writeFixed64(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.FIXED32:
            this.writeFixed32(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.BOOL:
            this.writeBool(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.STRING:
            this.writeString(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.GROUP:
            (0, goog.asserts.fail)("Group field type not supported in writeAny()");
            break;
          case module$contents$jspb$BinaryConstants_FieldType.MESSAGE:
            (0, goog.asserts.fail)("Message field type not supported in writeAny()");
            break;
          case module$contents$jspb$BinaryConstants_FieldType.BYTES:
            this.writeBytes(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.UINT32:
            this.writeUint32(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.ENUM:
            this.writeEnum(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.SFIXED32:
            this.writeSfixed32(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.SFIXED64:
            this.writeSfixed64(
              b2,
              c
            );
            break;
          case module$contents$jspb$BinaryConstants_FieldType.SINT32:
            this.writeSint32(b2, c);
            break;
          case module$contents$jspb$BinaryConstants_FieldType.SINT64:
            this.writeSint64(b2, c);
            break;
          default:
            (0, goog.asserts.fail)("Invalid field type in writeAny()");
        }
      }
      writeUnsignedVarint32_(a2, b2) {
        null != b2 && (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeUnsignedVarint32(b2));
      }
      writeSignedVarint32_(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertSignedInteger(a2, b2), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeSignedVarint32(b2));
      }
      writeUnsignedVarint64_(a2, b2) {
        if (null != b2) switch (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), typeof b2) {
          case "number":
            this.encoder_.writeUnsignedVarint64(b2);
            break;
          case "bigint":
            a2 = module$contents$jspb$arith_UInt64.fromBigInt(b2);
            this.encoder_.writeSplitVarint64(a2.lo, a2.hi);
            break;
          default:
            a2 = module$contents$jspb$arith_UInt64.fromString(b2), this.encoder_.writeSplitVarint64(
              a2.lo,
              a2.hi
            );
        }
      }
      writeSignedVarint64_(a2, b2) {
        if (null != b2) switch (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), typeof b2) {
          case "number":
            this.encoder_.writeSignedVarint64(b2);
            break;
          case "bigint":
            a2 = module$contents$jspb$arith_Int64.fromBigInt(b2);
            this.encoder_.writeSplitVarint64(a2.lo, a2.hi);
            break;
          default:
            a2 = module$contents$jspb$arith_Int64.fromString(b2), this.encoder_.writeSplitVarint64(a2.lo, a2.hi);
        }
      }
      writeZigzagVarint32_(a2, b2) {
        null != b2 && (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeZigzagVarint32(b2));
      }
      writeZigzagVarint64_(a2, b2) {
        if (null != b2) switch (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), typeof b2) {
          case "number":
            this.encoder_.writeZigzagVarint64(b2);
            break;
          default:
            this.encoder_.writeZigzagVarint64String(b2);
        }
      }
      writeInt32(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_31), this.writeSignedVarint32_(a2, b2));
      }
      writeInt64(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertSignedInt64(a2, b2), this.writeSignedVarint64_(a2, b2));
      }
      writeInt64String(a2, b2) {
        this.writeInt64(a2, b2);
      }
      writeUint32(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, 0 <= b2 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_32), this.writeUnsignedVarint32_(a2, b2));
      }
      writeUint64(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertUnsignedInt64(a2, b2), this.writeUnsignedVarint64_(a2, b2));
      }
      writeUint64String(a2, b2) {
        this.writeUint64(a2, b2);
      }
      writeSint32(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_31), this.writeZigzagVarint32_(a2, b2));
      }
      writeSint64(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertSignedInt64(a2, b2), this.writeZigzagVarint64_(a2, b2));
      }
      writeSint64String(a2, b2) {
        this.writeSint64(a2, b2);
      }
      writeFixed32(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, 0 <= b2 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_32), this.writeFieldHeader_(
          a2,
          module$contents$jspb$BinaryConstants_WireType.FIXED32
        ), this.encoder_.writeUint32(b2));
      }
      writeFixed64(a2, b2) {
        if (null != b2) switch (module$contents$jspb$binary$writer_assertUnsignedInt64(a2, b2), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.FIXED64), typeof b2) {
          case "number":
            this.encoder_.writeUint64(b2);
            break;
          case "bigint":
            a2 = module$contents$jspb$arith_UInt64.fromBigInt(b2);
            this.encoder_.writeSplitFixed64(a2.lo, a2.hi);
            break;
          default:
            a2 = module$contents$jspb$arith_UInt64.fromString(b2), this.encoder_.writeSplitFixed64(
              a2.lo,
              a2.hi
            );
        }
      }
      writeFixed64String(a2, b2) {
        this.writeFixed64(a2, b2);
      }
      writeSfixed32(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_31), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.FIXED32), this.encoder_.writeInt32(b2));
      }
      writeSfixed64(a2, b2) {
        if (null != b2) switch (module$contents$jspb$binary$writer_assertSignedInt64(a2, b2), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.FIXED64), typeof b2) {
          case "number":
            this.encoder_.writeInt64(b2);
            break;
          case "bigint":
            a2 = module$contents$jspb$arith_Int64.fromBigInt(b2);
            this.encoder_.writeSplitFixed64(a2.lo, a2.hi);
            break;
          default:
            a2 = module$contents$jspb$arith_Int64.fromString(b2), this.encoder_.writeSplitFixed64(a2.lo, a2.hi);
        }
      }
      writeSfixed64String(a2, b2) {
        this.writeSfixed64(a2, b2);
      }
      writeFloat(a2, b2) {
        null != b2 && (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.FIXED32), this.encoder_.writeFloat(b2));
      }
      writeDouble(a2, b2) {
        null != b2 && (this.writeFieldHeader_(
          a2,
          module$contents$jspb$BinaryConstants_WireType.FIXED64
        ), this.encoder_.writeDouble(b2));
      }
      writeBool(a2, b2) {
        null != b2 && (module$contents$jspb$binary$writer_assertThat(a2, b2, "boolean" === typeof b2 || "number" === typeof b2), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeBool(b2));
      }
      writeEnum(a2, b2) {
        null != b2 && (b2 = parseInt(b2, 10), module$contents$jspb$binary$writer_assertSignedInteger(a2, b2), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeSignedVarint32(b2));
      }
      writeString(a2, b2) {
        null != b2 && this.writeUint8Array(a2, module$contents$jspb$binary$utf8_encodeUtf8(b2, module$contents$jspb$binary$writer_REJECT_UNPAIRED_SURROGATES));
      }
      writeBytes(a2, b2) {
        null != b2 && this.writeUint8Array(a2, module$contents$jspb$binary$internal_buffer_bufferFromSource(b2, true).buffer);
      }
      writeUint8Array(a2, b2) {
        this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED);
        this.encoder_.writeUnsignedVarint32(b2.length);
        this.appendUint8Array_(b2);
      }
      writeMessage(a2, b2, c) {
        null != b2 && (a2 = this.beginDelimited_(a2), c(
          b2,
          this
        ), this.endDelimited_(a2));
      }
      writeMessageSet(a2, b2, c) {
        null != b2 && (this.writeFieldHeader_(1, module$contents$jspb$BinaryConstants_WireType.START_GROUP), this.writeFieldHeader_(2, module$contents$jspb$BinaryConstants_WireType.VARINT), this.encoder_.writeSignedVarint32(a2), a2 = this.beginDelimited_(3), c(b2, this), this.endDelimited_(a2), this.writeFieldHeader_(1, module$contents$jspb$BinaryConstants_WireType.END_GROUP));
      }
      writeGroup(a2, b2, c) {
        null != b2 && (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.START_GROUP), c(b2, this), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.END_GROUP));
      }
      writeSplitFixed64(a2, b2, c) {
        this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.FIXED64);
        this.encoder_.writeSplitFixed64(b2, c);
      }
      writeSplitVarint64(a2, b2, c) {
        this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT);
        this.encoder_.writeSplitVarint64(b2, c);
      }
      writeSplitZigzagVarint64(a2, b2, c) {
        this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.VARINT);
        this.encoder_.writeSplitZigzagVarint64(b2 >>> 0, c >>> 0);
      }
      writeRepeatedInt32(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeSignedVarint32_(a2, b2[c]);
      }
      writeRepeatedInt64(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeSignedVarint64_(a2, b2[c]);
      }
      writeRepeatedSplitFixed64(a2, b2, c, d) {
        if (null != b2) for (let e = 0; e < b2.length; e++) this.writeSplitFixed64(a2, c(b2[e]), d(b2[e]));
      }
      writeRepeatedSplitVarint64(a2, b2, c, d) {
        if (null != b2) for (let e = 0; e < b2.length; e++) this.writeSplitVarint64(a2, c(b2[e]), d(b2[e]));
      }
      writeRepeatedSplitZigzagVarint64(a2, b2, c, d) {
        if (null != b2) for (let e = 0; e < b2.length; e++) this.writeSplitZigzagVarint64(
          a2,
          c(b2[e]),
          d(b2[e])
        );
      }
      writeRepeatedInt64String(a2, b2) {
        this.writeRepeatedInt64(a2, b2);
      }
      writeRepeatedUint32(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeUnsignedVarint32_(a2, b2[c]);
      }
      writeRepeatedUint64(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeUnsignedVarint64_(a2, b2[c]);
      }
      writeRepeatedUint64String(a2, b2) {
        this.writeRepeatedUint64(a2, b2);
      }
      writeRepeatedSint32(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeZigzagVarint32_(a2, b2[c]);
      }
      writeRepeatedSint64(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeZigzagVarint64_(
          a2,
          b2[c]
        );
      }
      writeRepeatedSint64String(a2, b2) {
        this.writeRepeatedSint64(a2, b2);
      }
      writeRepeatedFixed32(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeFixed32(a2, b2[c]);
      }
      writeRepeatedFixed64(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeFixed64(a2, b2[c]);
      }
      writeRepeatedFixed64String(a2, b2) {
        this.writeRepeatedFixed64(a2, b2);
      }
      writeRepeatedSfixed32(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeSfixed32(a2, b2[c]);
      }
      writeRepeatedSfixed64(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeSfixed64(a2, b2[c]);
      }
      writeRepeatedSfixed64String(a2, b2) {
        this.writeRepeatedSfixed64(a2, b2);
      }
      writeRepeatedFloat(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeFloat(a2, b2[c]);
      }
      writeRepeatedDouble(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeDouble(a2, b2[c]);
      }
      writeRepeatedBool(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeBool(a2, b2[c]);
      }
      writeRepeatedEnum(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeEnum(a2, b2[c]);
      }
      writeRepeatedString(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeString(a2, b2[c]);
      }
      writeRepeatedBytes(a2, b2) {
        if (null != b2) for (let c = 0; c < b2.length; c++) this.writeBytes(a2, b2[c]);
      }
      writeRepeatedMessage(a2, b2, c) {
        if (null != b2) for (let d = 0; d < b2.length; d++) {
          const e = this.beginDelimited_(a2);
          c(b2[d], this);
          this.endDelimited_(e);
        }
      }
      writeRepeatedGroup(a2, b2, c) {
        if (null != b2) for (let d = 0; d < b2.length; d++) this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.START_GROUP), c(b2[d], this), this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.END_GROUP);
      }
      writePackedInt32(a2, b2) {
        if (null != b2 && b2.length) {
          var c = this.beginDelimited_(a2);
          for (let d = 0; d < b2.length; d++) module$contents$jspb$binary$writer_assertSignedInteger(a2, b2[d]), this.encoder_.writeSignedVarint32(b2[d]);
          this.endDelimited_(c);
        }
      }
      writePackedInt32String(a2, b2) {
        if (null != b2 && b2.length) {
          var c = this.beginDelimited_(a2);
          for (let d = 0; d < b2.length; d++) {
            const e = parseInt(b2[d], 10);
            module$contents$jspb$binary$writer_assertSignedInteger(a2, e);
            this.encoder_.writeSignedVarint32(e);
          }
          this.endDelimited_(c);
        }
      }
      writePackedInt64(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let d = 0; d < b2.length; d++) {
            var c = b2[d];
            switch (typeof c) {
              case "number":
                this.encoder_.writeSignedVarint64(c);
                break;
              case "bigint":
                c = module$contents$jspb$arith_Int64.fromBigInt(c);
                this.encoder_.writeSplitVarint64(c.lo, c.hi);
                break;
              default:
                c = module$contents$jspb$arith_Int64.fromString(c), this.encoder_.writeSplitVarint64(c.lo, c.hi);
            }
          }
          this.endDelimited_(a2);
        }
      }
      writePackedSplitFixed64(a2, b2, c, d) {
        if (null != b2) {
          a2 = this.beginDelimited_(a2);
          for (let e = 0; e < b2.length; e++) this.encoder_.writeSplitFixed64(c(b2[e]), d(b2[e]));
          this.endDelimited_(a2);
        }
      }
      writePackedSplitVarint64(a2, b2, c, d) {
        if (null != b2) {
          a2 = this.beginDelimited_(a2);
          for (let e = 0; e < b2.length; e++) this.encoder_.writeSplitVarint64(c(b2[e]), d(b2[e]));
          this.endDelimited_(a2);
        }
      }
      writePackedSplitZigzagVarint64(a2, b2, c, d) {
        if (null != b2) {
          a2 = this.beginDelimited_(a2);
          var e = this.encoder_;
          for (let f = 0; f < b2.length; f++) e.writeSplitZigzagVarint64(c(b2[f]), d(b2[f]));
          this.endDelimited_(a2);
        }
      }
      writePackedInt64String(a2, b2) {
        this.writePackedInt64(a2, b2);
      }
      writePackedUint32(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let c = 0; c < b2.length; c++) this.encoder_.writeUnsignedVarint32(b2[c]);
          this.endDelimited_(a2);
        }
      }
      writePackedUint64(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let d = 0; d < b2.length; d++) {
            var c = b2[d];
            switch (typeof c) {
              case "number":
                this.encoder_.writeUnsignedVarint64(c);
                break;
              case "bigint":
                const e = Number(c);
                Number.isSafeInteger(e) ? this.encoder_.writeUnsignedVarint64(e) : (c = module$contents$jspb$arith_UInt64.fromBigInt(c), this.encoder_.writeSplitVarint64(c.lo, c.hi));
                break;
              default:
                c = module$contents$jspb$arith_UInt64.fromString(c), this.encoder_.writeSplitVarint64(
                  c.lo,
                  c.hi
                );
            }
          }
          this.endDelimited_(a2);
        }
      }
      writePackedUint64String(a2, b2) {
        this.writePackedUint64(a2, b2);
      }
      writePackedSint32(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let c = 0; c < b2.length; c++) this.encoder_.writeZigzagVarint32(b2[c]);
          this.endDelimited_(a2);
        }
      }
      writePackedSint64(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let c = 0; c < b2.length; c++) {
            const d = b2[c];
            switch (typeof d) {
              case "number":
                this.encoder_.writeZigzagVarint64(d);
                break;
              default:
                this.encoder_.writeZigzagVarint64String(d);
            }
          }
          this.endDelimited_(a2);
        }
      }
      writePackedSint64String(a2, b2) {
        this.writePackedSint64(a2, b2);
      }
      writePackedFixed32(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(4 * b2.length), a2 = 0; a2 < b2.length; a2++) this.encoder_.writeUint32(b2[a2]);
      }
      writePackedFixed64(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(8 * b2.length), a2 = 0; a2 < b2.length; a2++) {
          var c = b2[a2];
          switch (typeof c) {
            case "number":
              this.encoder_.writeUint64(c);
              break;
            case "bigint":
              c = module$contents$jspb$arith_UInt64.fromBigInt(c);
              this.encoder_.writeSplitFixed64(c.lo, c.hi);
              break;
            default:
              c = module$contents$jspb$arith_UInt64.fromString(c), this.encoder_.writeSplitFixed64(c.lo, c.hi);
          }
        }
      }
      writePackedFixed64String(a2, b2) {
        this.writePackedFixed64(a2, b2);
      }
      writePackedSfixed32(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(4 * b2.length), a2 = 0; a2 < b2.length; a2++) this.encoder_.writeInt32(b2[a2]);
      }
      writePackedSfixed64(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(8 * b2.length), a2 = 0; a2 < b2.length; a2++) {
          var c = b2[a2];
          switch (typeof c) {
            case "number":
              this.encoder_.writeInt64(c);
              break;
            case "bigint":
              c = module$contents$jspb$arith_Int64.fromBigInt(c);
              this.encoder_.writeSplitFixed64(c.lo, c.hi);
              break;
            default:
              c = module$contents$jspb$arith_Int64.fromString(c), this.encoder_.writeSplitFixed64(c.lo, c.hi);
          }
        }
      }
      writePackedSfixed64String(a2, b2) {
        this.writePackedSfixed64(
          a2,
          b2
        );
      }
      writePackedFloat(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(4 * b2.length), a2 = 0; a2 < b2.length; a2++) this.encoder_.writeFloat(b2[a2]);
      }
      writePackedDouble(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(a2, module$contents$jspb$BinaryConstants_WireType.DELIMITED), this.encoder_.writeUnsignedVarint32(8 * b2.length), a2 = 0; a2 < b2.length; a2++) this.encoder_.writeDouble(b2[a2]);
      }
      writePackedBool(a2, b2) {
        if (null != b2 && b2.length) for (this.writeFieldHeader_(
          a2,
          module$contents$jspb$BinaryConstants_WireType.DELIMITED
        ), this.encoder_.writeUnsignedVarint32(b2.length), a2 = 0; a2 < b2.length; a2++) this.encoder_.writeBool(b2[a2]);
      }
      writePackedEnum(a2, b2) {
        if (null != b2 && b2.length) {
          a2 = this.beginDelimited_(a2);
          for (let c = 0; c < b2.length; c++) this.encoder_.writeEnum(b2[c]);
          this.endDelimited_(a2);
        }
      }
    };
    function module$contents$jspb$binary$writer_assertSignedInteger(a2, b2) {
      module$contents$jspb$binary$writer_assertThat(a2, b2, b2 === Math.floor(b2));
      module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= -module$contents$jspb$BinaryConstants_TWO_TO_31 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_31);
    }
    function module$contents$jspb$binary$writer_assertSignedInt64(a2, b2) {
      switch (typeof b2) {
        case "string":
          module$contents$jspb$binary$writer_assertThat(a2, b2, module$contents$jspb$arith_Int64.fromString(b2));
          break;
        case "number":
          module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= -module$contents$jspb$BinaryConstants_TWO_TO_63 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_63);
          break;
        default:
          module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= BigInt(-module$contents$jspb$BinaryConstants_TWO_TO_63) && b2 < BigInt(module$contents$jspb$BinaryConstants_TWO_TO_63));
      }
    }
    function module$contents$jspb$binary$writer_assertUnsignedInt64(a2, b2) {
      switch (typeof b2) {
        case "string":
          module$contents$jspb$binary$writer_assertThat(a2, b2, module$contents$jspb$arith_UInt64.fromString(b2));
          break;
        case "number":
          module$contents$jspb$binary$writer_assertThat(a2, b2, 0 <= b2 && b2 < module$contents$jspb$BinaryConstants_TWO_TO_64);
          break;
        default:
          module$contents$jspb$binary$writer_assertThat(a2, b2, b2 >= BigInt(0) && b2 < BigInt(module$contents$jspb$BinaryConstants_TWO_TO_64));
      }
    }
    function module$contents$jspb$binary$writer_assertThat(a2, b2, c) {
      c || (0, goog.asserts.fail)(`for [${b2}] at [${a2}]`);
    }
    jspb.binary.writer.BinaryWriter = module$contents$jspb$binary$writer_BinaryWriter;
    jspb.BinaryWriter = module$contents$jspb$binary$writer_BinaryWriter;
    jspb.internal = {};
    jspb.internal.public_for_gencode = {};
    function module$contents$jspb$internal$public_for_gencode_serializeMapToBinary(a2, b2, c, d, e, f) {
      a2 && a2.forEach((g, h) => {
        c.writeMessage(b2, a2, (l, k) => {
          d.call(k, 1, h);
          e.call(k, 2, g, f);
        });
      });
    }
    function module$contents$jspb$internal$public_for_gencode_deserializeMapFromBinary(a2, b2, c, d, e, f) {
      b2.readMessage(a2, (g, h) => {
        g = d;
        let l = f;
        for (; h.nextField() && !h.isEndGroup(); ) {
          const k = h.getFieldNumber();
          1 == k ? g = c.call(h) : 2 == k && (a2.valueCtor ? h.readMessage(l, e) : l = e.call(h));
        }
        goog.asserts.assert(void 0 != g);
        goog.asserts.assert(void 0 != l);
        a2.set(g, l);
      });
    }
    jspb.internal.public_for_gencode.deserializeMapFromBinary = module$contents$jspb$internal$public_for_gencode_deserializeMapFromBinary;
    jspb.internal.public_for_gencode.serializeMapToBinary = module$contents$jspb$internal$public_for_gencode_serializeMapToBinary;
    jspb.Export = {};
    "object" === typeof exports && (exports.debug = jspb.debug, exports.Map = module$contents$jspb$Map_Map, exports.Message = module$contents$jspb$Message_Message, exports.BinaryReader = module$contents$jspb$binary$reader_BinaryReader, exports.BinaryWriter = module$contents$jspb$binary$writer_BinaryWriter, exports.ExtensionFieldInfo = module$contents$jspb$ExtensionFieldInfo_ExtensionFieldInfo, exports.ExtensionFieldBinaryInfo = module$contents$jspb$ExtensionFieldBinaryInfo_ExtensionFieldBinaryInfo, exports.internal = { public_for_gencode: jspb.internal.public_for_gencode }, exports.exportSymbol = goog.exportSymbol, exports.inherits = goog.inherits, exports.object = { extend: module$contents$goog$object_extend }, exports.typeOf = goog.typeOf);
  }
});

// static/js/grpc-generated/scp_cv/v1/control_pb.js
var require_control_pb = __commonJS({
  "static/js/grpc-generated/scp_cv/v1/control_pb.js"(exports2) {
    var jspb2 = require_google_protobuf();
    var goog2 = jspb2;
    var global = globalThis;
    goog2.exportSymbol("proto.scp_cv.v1.ActivateScenarioReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ActivateScenarioRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.AddLocalPathSourceRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.AddWebUrlSourceRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.AllSessionSnapshotsReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.CloseSourceRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ControlPlaybackRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.DeleteScenarioRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.DeleteSourceRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.DisplayTargetItem", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.DisplayTargetsReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.EmptyRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ListScenariosReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ListSourcesReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ListSourcesRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.NavigateAction", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.NavigateContentRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.OpenSourceRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.OperationReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.PlaybackAction", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.PlaybackStateEvent", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.PlaybackStateReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.RuntimeStatusReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ScenarioDetail", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ScenarioItem", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ScenarioReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ScenarioWindowSlot", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SelectDisplayTargetRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SessionSnapshot", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SetSpliceModeRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SourceItem", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SourceReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SourceType", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.SpliceModeReply", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.ToggleLoopRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.UpdateScenarioRequest", null, global);
    goog2.exportSymbol("proto.scp_cv.v1.WindowRequest", null, global);
    proto.scp_cv.v1.EmptyRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.EmptyRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.EmptyRequest.displayName = "proto.scp_cv.v1.EmptyRequest";
    }
    proto.scp_cv.v1.WindowRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.WindowRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.WindowRequest.displayName = "proto.scp_cv.v1.WindowRequest";
    }
    proto.scp_cv.v1.OpenSourceRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.OpenSourceRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.OpenSourceRequest.displayName = "proto.scp_cv.v1.OpenSourceRequest";
    }
    proto.scp_cv.v1.CloseSourceRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.CloseSourceRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.CloseSourceRequest.displayName = "proto.scp_cv.v1.CloseSourceRequest";
    }
    proto.scp_cv.v1.ControlPlaybackRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ControlPlaybackRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ControlPlaybackRequest.displayName = "proto.scp_cv.v1.ControlPlaybackRequest";
    }
    proto.scp_cv.v1.NavigateContentRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.NavigateContentRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.NavigateContentRequest.displayName = "proto.scp_cv.v1.NavigateContentRequest";
    }
    proto.scp_cv.v1.SelectDisplayTargetRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.SelectDisplayTargetRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SelectDisplayTargetRequest.displayName = "proto.scp_cv.v1.SelectDisplayTargetRequest";
    }
    proto.scp_cv.v1.OperationReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.OperationReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.OperationReply.displayName = "proto.scp_cv.v1.OperationReply";
    }
    proto.scp_cv.v1.RuntimeStatusReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.RuntimeStatusReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.RuntimeStatusReply.displayName = "proto.scp_cv.v1.RuntimeStatusReply";
    }
    proto.scp_cv.v1.PlaybackStateReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.PlaybackStateReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.PlaybackStateReply.displayName = "proto.scp_cv.v1.PlaybackStateReply";
    }
    proto.scp_cv.v1.DisplayTargetItem = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.DisplayTargetItem, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.DisplayTargetItem.displayName = "proto.scp_cv.v1.DisplayTargetItem";
    }
    proto.scp_cv.v1.DisplayTargetsReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.DisplayTargetsReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.DisplayTargetsReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.DisplayTargetsReply.displayName = "proto.scp_cv.v1.DisplayTargetsReply";
    }
    proto.scp_cv.v1.ListSourcesRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ListSourcesRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ListSourcesRequest.displayName = "proto.scp_cv.v1.ListSourcesRequest";
    }
    proto.scp_cv.v1.SourceItem = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.SourceItem, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SourceItem.displayName = "proto.scp_cv.v1.SourceItem";
    }
    proto.scp_cv.v1.ListSourcesReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.ListSourcesReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.ListSourcesReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ListSourcesReply.displayName = "proto.scp_cv.v1.ListSourcesReply";
    }
    proto.scp_cv.v1.AddLocalPathSourceRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.AddLocalPathSourceRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.AddLocalPathSourceRequest.displayName = "proto.scp_cv.v1.AddLocalPathSourceRequest";
    }
    proto.scp_cv.v1.AddWebUrlSourceRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.AddWebUrlSourceRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.AddWebUrlSourceRequest.displayName = "proto.scp_cv.v1.AddWebUrlSourceRequest";
    }
    proto.scp_cv.v1.SourceReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.SourceReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SourceReply.displayName = "proto.scp_cv.v1.SourceReply";
    }
    proto.scp_cv.v1.DeleteSourceRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.DeleteSourceRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.DeleteSourceRequest.displayName = "proto.scp_cv.v1.DeleteSourceRequest";
    }
    proto.scp_cv.v1.ToggleLoopRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ToggleLoopRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ToggleLoopRequest.displayName = "proto.scp_cv.v1.ToggleLoopRequest";
    }
    proto.scp_cv.v1.SetSpliceModeRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.SetSpliceModeRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SetSpliceModeRequest.displayName = "proto.scp_cv.v1.SetSpliceModeRequest";
    }
    proto.scp_cv.v1.SpliceModeReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.SpliceModeReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.SpliceModeReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SpliceModeReply.displayName = "proto.scp_cv.v1.SpliceModeReply";
    }
    proto.scp_cv.v1.SessionSnapshot = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.SessionSnapshot, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.SessionSnapshot.displayName = "proto.scp_cv.v1.SessionSnapshot";
    }
    proto.scp_cv.v1.AllSessionSnapshotsReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.AllSessionSnapshotsReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.AllSessionSnapshotsReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.AllSessionSnapshotsReply.displayName = "proto.scp_cv.v1.AllSessionSnapshotsReply";
    }
    proto.scp_cv.v1.ScenarioWindowSlot = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ScenarioWindowSlot, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ScenarioWindowSlot.displayName = "proto.scp_cv.v1.ScenarioWindowSlot";
    }
    proto.scp_cv.v1.ScenarioDetail = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ScenarioDetail, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ScenarioDetail.displayName = "proto.scp_cv.v1.ScenarioDetail";
    }
    proto.scp_cv.v1.ScenarioItem = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ScenarioItem, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ScenarioItem.displayName = "proto.scp_cv.v1.ScenarioItem";
    }
    proto.scp_cv.v1.ListScenariosReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.ListScenariosReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.ListScenariosReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ListScenariosReply.displayName = "proto.scp_cv.v1.ListScenariosReply";
    }
    proto.scp_cv.v1.UpdateScenarioRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.UpdateScenarioRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.UpdateScenarioRequest.displayName = "proto.scp_cv.v1.UpdateScenarioRequest";
    }
    proto.scp_cv.v1.DeleteScenarioRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.DeleteScenarioRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.DeleteScenarioRequest.displayName = "proto.scp_cv.v1.DeleteScenarioRequest";
    }
    proto.scp_cv.v1.ActivateScenarioRequest = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ActivateScenarioRequest, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ActivateScenarioRequest.displayName = "proto.scp_cv.v1.ActivateScenarioRequest";
    }
    proto.scp_cv.v1.ScenarioReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, null, null);
    };
    goog2.inherits(proto.scp_cv.v1.ScenarioReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ScenarioReply.displayName = "proto.scp_cv.v1.ScenarioReply";
    }
    proto.scp_cv.v1.ActivateScenarioReply = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.ActivateScenarioReply.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.ActivateScenarioReply, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.ActivateScenarioReply.displayName = "proto.scp_cv.v1.ActivateScenarioReply";
    }
    proto.scp_cv.v1.PlaybackStateEvent = function(opt_data) {
      jspb2.Message.initialize(this, opt_data, 0, -1, proto.scp_cv.v1.PlaybackStateEvent.repeatedFields_, null);
    };
    goog2.inherits(proto.scp_cv.v1.PlaybackStateEvent, jspb2.Message);
    if (goog2.DEBUG && !COMPILED) {
      proto.scp_cv.v1.PlaybackStateEvent.displayName = "proto.scp_cv.v1.PlaybackStateEvent";
    }
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.EmptyRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.EmptyRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.EmptyRequest.toObject = function(includeInstance, msg) {
        var f, obj = {};
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.EmptyRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.EmptyRequest();
      return proto.scp_cv.v1.EmptyRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.EmptyRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.EmptyRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.EmptyRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.EmptyRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.WindowRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.WindowRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.WindowRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          windowId: jspb2.Message.getFieldWithDefault(msg, 1, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.WindowRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.WindowRequest();
      return proto.scp_cv.v1.WindowRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.WindowRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.WindowRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.WindowRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.WindowRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.WindowRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.WindowRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.OpenSourceRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.OpenSourceRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.OpenSourceRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          mediaSourceId: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          autoplay: jspb2.Message.getBooleanFieldWithDefault(msg, 2, false),
          windowId: jspb2.Message.getFieldWithDefault(msg, 3, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.OpenSourceRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.OpenSourceRequest();
      return proto.scp_cv.v1.OpenSourceRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.OpenSourceRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setMediaSourceId(value);
            break;
          case 2:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setAutoplay(value);
            break;
          case 3:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.OpenSourceRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.OpenSourceRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getMediaSourceId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
      f = message.getAutoplay();
      if (f) {
        writer.writeBool(
          2,
          f
        );
      }
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          3,
          f
        );
      }
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.getMediaSourceId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.setMediaSourceId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.getAutoplay = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 2, false)
      );
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.setAutoplay = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 2, value);
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 3, 0)
      );
    };
    proto.scp_cv.v1.OpenSourceRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 3, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.CloseSourceRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.CloseSourceRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.CloseSourceRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          windowId: jspb2.Message.getFieldWithDefault(msg, 1, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.CloseSourceRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.CloseSourceRequest();
      return proto.scp_cv.v1.CloseSourceRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.CloseSourceRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.CloseSourceRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.CloseSourceRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.CloseSourceRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.CloseSourceRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.CloseSourceRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ControlPlaybackRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ControlPlaybackRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ControlPlaybackRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          action: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          windowId: jspb2.Message.getFieldWithDefault(msg, 2, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ControlPlaybackRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ControlPlaybackRequest();
      return proto.scp_cv.v1.ControlPlaybackRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ControlPlaybackRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {!proto.scp_cv.v1.PlaybackAction} */
              reader.readEnum()
            );
            msg.setAction(value);
            break;
          case 2:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ControlPlaybackRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ControlPlaybackRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ControlPlaybackRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getAction();
      if (f !== 0) {
        writer.writeEnum(
          1,
          f
        );
      }
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          2,
          f
        );
      }
    };
    proto.scp_cv.v1.ControlPlaybackRequest.prototype.getAction = function() {
      return (
        /** @type {!proto.scp_cv.v1.PlaybackAction} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.ControlPlaybackRequest.prototype.setAction = function(value) {
      return jspb2.Message.setProto3EnumField(this, 1, value);
    };
    proto.scp_cv.v1.ControlPlaybackRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 2, 0)
      );
    };
    proto.scp_cv.v1.ControlPlaybackRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 2, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.NavigateContentRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.NavigateContentRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.NavigateContentRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          action: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          targetIndex: jspb2.Message.getFieldWithDefault(msg, 2, 0),
          positionMs: jspb2.Message.getFieldWithDefault(msg, 3, 0),
          windowId: jspb2.Message.getFieldWithDefault(msg, 4, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.NavigateContentRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.NavigateContentRequest();
      return proto.scp_cv.v1.NavigateContentRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.NavigateContentRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {!proto.scp_cv.v1.NavigateAction} */
              reader.readEnum()
            );
            msg.setAction(value);
            break;
          case 2:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setTargetIndex(value);
            break;
          case 3:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setPositionMs(value);
            break;
          case 4:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.NavigateContentRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.NavigateContentRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getAction();
      if (f !== 0) {
        writer.writeEnum(
          1,
          f
        );
      }
      f = message.getTargetIndex();
      if (f !== 0) {
        writer.writeInt32(
          2,
          f
        );
      }
      f = message.getPositionMs();
      if (f !== 0) {
        writer.writeInt64(
          3,
          f
        );
      }
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          4,
          f
        );
      }
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.getAction = function() {
      return (
        /** @type {!proto.scp_cv.v1.NavigateAction} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.setAction = function(value) {
      return jspb2.Message.setProto3EnumField(this, 1, value);
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.getTargetIndex = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 2, 0)
      );
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.setTargetIndex = function(value) {
      return jspb2.Message.setProto3IntField(this, 2, value);
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.getPositionMs = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 3, 0)
      );
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.setPositionMs = function(value) {
      return jspb2.Message.setProto3IntField(this, 3, value);
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 4, 0)
      );
    };
    proto.scp_cv.v1.NavigateContentRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 4, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SelectDisplayTargetRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SelectDisplayTargetRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          displayMode: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          targetLabel: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          windowId: jspb2.Message.getFieldWithDefault(msg, 3, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SelectDisplayTargetRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SelectDisplayTargetRequest();
      return proto.scp_cv.v1.SelectDisplayTargetRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDisplayMode(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setTargetLabel(value);
            break;
          case 3:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SelectDisplayTargetRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getDisplayMode();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getTargetLabel();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          3,
          f
        );
      }
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.getDisplayMode = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.setDisplayMode = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.getTargetLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.setTargetLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 3, 0)
      );
    };
    proto.scp_cv.v1.SelectDisplayTargetRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 3, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.OperationReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.OperationReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.OperationReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          message: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          detail: jspb2.Message.getFieldWithDefault(msg, 3, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.OperationReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.OperationReply();
      return proto.scp_cv.v1.OperationReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.OperationReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setMessage(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDetail(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.OperationReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.OperationReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.OperationReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getMessage();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getDetail();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
    };
    proto.scp_cv.v1.OperationReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.OperationReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.OperationReply.prototype.getMessage = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.OperationReply.prototype.setMessage = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.OperationReply.prototype.getDetail = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.OperationReply.prototype.setDetail = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.RuntimeStatusReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.RuntimeStatusReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.RuntimeStatusReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          sourceType: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          sourceName: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          playbackState: jspb2.Message.getFieldWithDefault(msg, 3, ""),
          displayMode: jspb2.Message.getFieldWithDefault(msg, 4, ""),
          grpcEndpoint: jspb2.Message.getFieldWithDefault(msg, 5, ""),
          debugMode: jspb2.Message.getBooleanFieldWithDefault(msg, 6, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.RuntimeStatusReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.RuntimeStatusReply();
      return proto.scp_cv.v1.RuntimeStatusReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.RuntimeStatusReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceName(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPlaybackState(value);
            break;
          case 4:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDisplayMode(value);
            break;
          case 5:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setGrpcEndpoint(value);
            break;
          case 6:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setDebugMode(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.RuntimeStatusReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.RuntimeStatusReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getSourceName();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getPlaybackState();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
      f = message.getDisplayMode();
      if (f.length > 0) {
        writer.writeString(
          4,
          f
        );
      }
      f = message.getGrpcEndpoint();
      if (f.length > 0) {
        writer.writeString(
          5,
          f
        );
      }
      f = message.getDebugMode();
      if (f) {
        writer.writeBool(
          6,
          f
        );
      }
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getSourceName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setSourceName = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getPlaybackState = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setPlaybackState = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getDisplayMode = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 4, "")
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setDisplayMode = function(value) {
      return jspb2.Message.setProto3StringField(this, 4, value);
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getGrpcEndpoint = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 5, "")
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setGrpcEndpoint = function(value) {
      return jspb2.Message.setProto3StringField(this, 5, value);
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.getDebugMode = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 6, false)
      );
    };
    proto.scp_cv.v1.RuntimeStatusReply.prototype.setDebugMode = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 6, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.PlaybackStateReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.PlaybackStateReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.PlaybackStateReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          playbackState: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          sourceType: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          sourceName: jspb2.Message.getFieldWithDefault(msg, 3, ""),
          sourceUri: jspb2.Message.getFieldWithDefault(msg, 4, ""),
          currentSlide: jspb2.Message.getFieldWithDefault(msg, 5, 0),
          totalSlides: jspb2.Message.getFieldWithDefault(msg, 6, 0),
          positionMs: jspb2.Message.getFieldWithDefault(msg, 7, 0),
          durationMs: jspb2.Message.getFieldWithDefault(msg, 8, 0),
          displayMode: jspb2.Message.getFieldWithDefault(msg, 9, ""),
          targetDisplay: jspb2.Message.getFieldWithDefault(msg, 10, ""),
          isSpliced: jspb2.Message.getBooleanFieldWithDefault(msg, 11, false),
          loopEnabled: jspb2.Message.getBooleanFieldWithDefault(msg, 12, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.PlaybackStateReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.PlaybackStateReply();
      return proto.scp_cv.v1.PlaybackStateReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.PlaybackStateReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPlaybackState(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceName(value);
            break;
          case 4:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceUri(value);
            break;
          case 5:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setCurrentSlide(value);
            break;
          case 6:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setTotalSlides(value);
            break;
          case 7:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setPositionMs(value);
            break;
          case 8:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setDurationMs(value);
            break;
          case 9:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDisplayMode(value);
            break;
          case 10:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setTargetDisplay(value);
            break;
          case 11:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsSpliced(value);
            break;
          case 12:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setLoopEnabled(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.PlaybackStateReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.PlaybackStateReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getPlaybackState();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getSourceName();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
      f = message.getSourceUri();
      if (f.length > 0) {
        writer.writeString(
          4,
          f
        );
      }
      f = message.getCurrentSlide();
      if (f !== 0) {
        writer.writeInt32(
          5,
          f
        );
      }
      f = message.getTotalSlides();
      if (f !== 0) {
        writer.writeInt32(
          6,
          f
        );
      }
      f = message.getPositionMs();
      if (f !== 0) {
        writer.writeInt64(
          7,
          f
        );
      }
      f = message.getDurationMs();
      if (f !== 0) {
        writer.writeInt64(
          8,
          f
        );
      }
      f = message.getDisplayMode();
      if (f.length > 0) {
        writer.writeString(
          9,
          f
        );
      }
      f = message.getTargetDisplay();
      if (f.length > 0) {
        writer.writeString(
          10,
          f
        );
      }
      f = message.getIsSpliced();
      if (f) {
        writer.writeBool(
          11,
          f
        );
      }
      f = message.getLoopEnabled();
      if (f) {
        writer.writeBool(
          12,
          f
        );
      }
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getPlaybackState = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setPlaybackState = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getSourceName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setSourceName = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getSourceUri = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 4, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setSourceUri = function(value) {
      return jspb2.Message.setProto3StringField(this, 4, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getCurrentSlide = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 5, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setCurrentSlide = function(value) {
      return jspb2.Message.setProto3IntField(this, 5, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getTotalSlides = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 6, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setTotalSlides = function(value) {
      return jspb2.Message.setProto3IntField(this, 6, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getPositionMs = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 7, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setPositionMs = function(value) {
      return jspb2.Message.setProto3IntField(this, 7, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getDurationMs = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 8, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setDurationMs = function(value) {
      return jspb2.Message.setProto3IntField(this, 8, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getDisplayMode = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 9, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setDisplayMode = function(value) {
      return jspb2.Message.setProto3StringField(this, 9, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getTargetDisplay = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 10, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setTargetDisplay = function(value) {
      return jspb2.Message.setProto3StringField(this, 10, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getIsSpliced = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 11, false)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setIsSpliced = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 11, value);
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.getLoopEnabled = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 12, false)
      );
    };
    proto.scp_cv.v1.PlaybackStateReply.prototype.setLoopEnabled = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 12, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.DisplayTargetItem.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.DisplayTargetItem.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.DisplayTargetItem.toObject = function(includeInstance, msg) {
        var f, obj = {
          index: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          name: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          width: jspb2.Message.getFieldWithDefault(msg, 3, 0),
          height: jspb2.Message.getFieldWithDefault(msg, 4, 0),
          x: jspb2.Message.getFieldWithDefault(msg, 5, 0),
          y: jspb2.Message.getFieldWithDefault(msg, 6, 0),
          isPrimary: jspb2.Message.getBooleanFieldWithDefault(msg, 7, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.DisplayTargetItem.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.DisplayTargetItem();
      return proto.scp_cv.v1.DisplayTargetItem.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.DisplayTargetItem.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setIndex(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          case 3:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWidth(value);
            break;
          case 4:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setHeight(value);
            break;
          case 5:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setX(value);
            break;
          case 6:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setY(value);
            break;
          case 7:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsPrimary(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.DisplayTargetItem.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.DisplayTargetItem.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getIndex();
      if (f !== 0) {
        writer.writeInt32(
          1,
          f
        );
      }
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getWidth();
      if (f !== 0) {
        writer.writeInt32(
          3,
          f
        );
      }
      f = message.getHeight();
      if (f !== 0) {
        writer.writeInt32(
          4,
          f
        );
      }
      f = message.getX();
      if (f !== 0) {
        writer.writeInt32(
          5,
          f
        );
      }
      f = message.getY();
      if (f !== 0) {
        writer.writeInt32(
          6,
          f
        );
      }
      f = message.getIsPrimary();
      if (f) {
        writer.writeBool(
          7,
          f
        );
      }
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getIndex = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setIndex = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getWidth = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 3, 0)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setWidth = function(value) {
      return jspb2.Message.setProto3IntField(this, 3, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getHeight = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 4, 0)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setHeight = function(value) {
      return jspb2.Message.setProto3IntField(this, 4, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getX = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 5, 0)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setX = function(value) {
      return jspb2.Message.setProto3IntField(this, 5, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getY = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 6, 0)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setY = function(value) {
      return jspb2.Message.setProto3IntField(this, 6, value);
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.getIsPrimary = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 7, false)
      );
    };
    proto.scp_cv.v1.DisplayTargetItem.prototype.setIsPrimary = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 7, value);
    };
    proto.scp_cv.v1.DisplayTargetsReply.repeatedFields_ = [1];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.DisplayTargetsReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.DisplayTargetsReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.DisplayTargetsReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          targetsList: jspb2.Message.toObjectList(
            msg.getTargetsList(),
            proto.scp_cv.v1.DisplayTargetItem.toObject,
            includeInstance
          ),
          spliceLabel: jspb2.Message.getFieldWithDefault(msg, 2, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.DisplayTargetsReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.DisplayTargetsReply();
      return proto.scp_cv.v1.DisplayTargetsReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.DisplayTargetsReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = new proto.scp_cv.v1.DisplayTargetItem();
            reader.readMessage(value, proto.scp_cv.v1.DisplayTargetItem.deserializeBinaryFromReader);
            msg.addTargets(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSpliceLabel(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.DisplayTargetsReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.DisplayTargetsReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getTargetsList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          1,
          f,
          proto.scp_cv.v1.DisplayTargetItem.serializeBinaryToWriter
        );
      }
      f = message.getSpliceLabel();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.getTargetsList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.DisplayTargetItem>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.DisplayTargetItem, 1)
      );
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.setTargetsList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 1, value);
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.addTargets = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 1, opt_value, proto.scp_cv.v1.DisplayTargetItem, opt_index);
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.clearTargetsList = function() {
      return this.setTargetsList([]);
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.getSpliceLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.DisplayTargetsReply.prototype.setSpliceLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ListSourcesRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ListSourcesRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ListSourcesRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          sourceType: jspb2.Message.getFieldWithDefault(msg, 1, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ListSourcesRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ListSourcesRequest();
      return proto.scp_cv.v1.ListSourcesRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ListSourcesRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ListSourcesRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ListSourcesRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ListSourcesRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.ListSourcesRequest.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.ListSourcesRequest.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SourceItem.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SourceItem.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SourceItem.toObject = function(includeInstance, msg) {
        var f, obj = {
          id: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          sourceType: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          name: jspb2.Message.getFieldWithDefault(msg, 3, ""),
          uri: jspb2.Message.getFieldWithDefault(msg, 4, ""),
          isAvailable: jspb2.Message.getBooleanFieldWithDefault(msg, 5, false),
          streamIdentifier: jspb2.Message.getFieldWithDefault(msg, 6, ""),
          createdAt: jspb2.Message.getFieldWithDefault(msg, 7, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SourceItem.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SourceItem();
      return proto.scp_cv.v1.SourceItem.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SourceItem.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setId(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          case 4:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setUri(value);
            break;
          case 5:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsAvailable(value);
            break;
          case 6:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setStreamIdentifier(value);
            break;
          case 7:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setCreatedAt(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SourceItem.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SourceItem.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SourceItem.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
      f = message.getUri();
      if (f.length > 0) {
        writer.writeString(
          4,
          f
        );
      }
      f = message.getIsAvailable();
      if (f) {
        writer.writeBool(
          5,
          f
        );
      }
      f = message.getStreamIdentifier();
      if (f.length > 0) {
        writer.writeString(
          6,
          f
        );
      }
      f = message.getCreatedAt();
      if (f.length > 0) {
        writer.writeString(
          7,
          f
        );
      }
    };
    proto.scp_cv.v1.SourceItem.prototype.getId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getUri = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 4, "")
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setUri = function(value) {
      return jspb2.Message.setProto3StringField(this, 4, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getIsAvailable = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 5, false)
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setIsAvailable = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 5, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getStreamIdentifier = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 6, "")
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setStreamIdentifier = function(value) {
      return jspb2.Message.setProto3StringField(this, 6, value);
    };
    proto.scp_cv.v1.SourceItem.prototype.getCreatedAt = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 7, "")
      );
    };
    proto.scp_cv.v1.SourceItem.prototype.setCreatedAt = function(value) {
      return jspb2.Message.setProto3StringField(this, 7, value);
    };
    proto.scp_cv.v1.ListSourcesReply.repeatedFields_ = [2];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ListSourcesReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ListSourcesReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ListSourcesReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          sourcesList: jspb2.Message.toObjectList(
            msg.getSourcesList(),
            proto.scp_cv.v1.SourceItem.toObject,
            includeInstance
          )
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ListSourcesReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ListSourcesReply();
      return proto.scp_cv.v1.ListSourcesReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ListSourcesReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = new proto.scp_cv.v1.SourceItem();
            reader.readMessage(value, proto.scp_cv.v1.SourceItem.deserializeBinaryFromReader);
            msg.addSources(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ListSourcesReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ListSourcesReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getSourcesList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          2,
          f,
          proto.scp_cv.v1.SourceItem.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.getSourcesList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.SourceItem>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.SourceItem, 2)
      );
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.setSourcesList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 2, value);
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.addSources = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 2, opt_value, proto.scp_cv.v1.SourceItem, opt_index);
    };
    proto.scp_cv.v1.ListSourcesReply.prototype.clearSourcesList = function() {
      return this.setSourcesList([]);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.AddLocalPathSourceRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.AddLocalPathSourceRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          path: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          name: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          sourceType: jspb2.Message.getFieldWithDefault(msg, 3, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.AddLocalPathSourceRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.AddLocalPathSourceRequest();
      return proto.scp_cv.v1.AddLocalPathSourceRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPath(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.AddLocalPathSourceRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getPath();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.getPath = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.setPath = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.AddLocalPathSourceRequest.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.AddWebUrlSourceRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.AddWebUrlSourceRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          url: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          name: jspb2.Message.getFieldWithDefault(msg, 2, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.AddWebUrlSourceRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.AddWebUrlSourceRequest();
      return proto.scp_cv.v1.AddWebUrlSourceRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setUrl(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.AddWebUrlSourceRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getUrl();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.getUrl = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.setUrl = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.AddWebUrlSourceRequest.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SourceReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SourceReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SourceReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          message: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          source: (f = msg.getSource()) && proto.scp_cv.v1.SourceItem.toObject(includeInstance, f)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SourceReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SourceReply();
      return proto.scp_cv.v1.SourceReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SourceReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setMessage(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.SourceItem();
            reader.readMessage(value, proto.scp_cv.v1.SourceItem.deserializeBinaryFromReader);
            msg.setSource(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SourceReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SourceReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SourceReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getMessage();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getSource();
      if (f != null) {
        writer.writeMessage(
          3,
          f,
          proto.scp_cv.v1.SourceItem.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.SourceReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.SourceReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.SourceReply.prototype.getMessage = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.SourceReply.prototype.setMessage = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.SourceReply.prototype.getSource = function() {
      return (
        /** @type{?proto.scp_cv.v1.SourceItem} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.SourceItem, 3)
      );
    };
    proto.scp_cv.v1.SourceReply.prototype.setSource = function(value) {
      return jspb2.Message.setWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.SourceReply.prototype.clearSource = function() {
      return this.setSource(void 0);
    };
    proto.scp_cv.v1.SourceReply.prototype.hasSource = function() {
      return jspb2.Message.getField(this, 3) != null;
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.DeleteSourceRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.DeleteSourceRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.DeleteSourceRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          mediaSourceId: jspb2.Message.getFieldWithDefault(msg, 1, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.DeleteSourceRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.DeleteSourceRequest();
      return proto.scp_cv.v1.DeleteSourceRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.DeleteSourceRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setMediaSourceId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.DeleteSourceRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.DeleteSourceRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.DeleteSourceRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getMediaSourceId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.DeleteSourceRequest.prototype.getMediaSourceId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.DeleteSourceRequest.prototype.setMediaSourceId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ToggleLoopRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ToggleLoopRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ToggleLoopRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          windowId: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          enabled: jspb2.Message.getBooleanFieldWithDefault(msg, 2, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ToggleLoopRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ToggleLoopRequest();
      return proto.scp_cv.v1.ToggleLoopRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ToggleLoopRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          case 2:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setEnabled(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ToggleLoopRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ToggleLoopRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ToggleLoopRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          1,
          f
        );
      }
      f = message.getEnabled();
      if (f) {
        writer.writeBool(
          2,
          f
        );
      }
    };
    proto.scp_cv.v1.ToggleLoopRequest.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.ToggleLoopRequest.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.ToggleLoopRequest.prototype.getEnabled = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 2, false)
      );
    };
    proto.scp_cv.v1.ToggleLoopRequest.prototype.setEnabled = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 2, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SetSpliceModeRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SetSpliceModeRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SetSpliceModeRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          enabled: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SetSpliceModeRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SetSpliceModeRequest();
      return proto.scp_cv.v1.SetSpliceModeRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SetSpliceModeRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setEnabled(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SetSpliceModeRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SetSpliceModeRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SetSpliceModeRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getEnabled();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.SetSpliceModeRequest.prototype.getEnabled = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.SetSpliceModeRequest.prototype.setEnabled = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.SpliceModeReply.repeatedFields_ = [3];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SpliceModeReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SpliceModeReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SpliceModeReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          spliceActive: jspb2.Message.getBooleanFieldWithDefault(msg, 2, false),
          sessionsList: jspb2.Message.toObjectList(
            msg.getSessionsList(),
            proto.scp_cv.v1.SessionSnapshot.toObject,
            includeInstance
          )
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SpliceModeReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SpliceModeReply();
      return proto.scp_cv.v1.SpliceModeReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SpliceModeReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSpliceActive(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.SessionSnapshot();
            reader.readMessage(value, proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader);
            msg.addSessions(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SpliceModeReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SpliceModeReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getSpliceActive();
      if (f) {
        writer.writeBool(
          2,
          f
        );
      }
      f = message.getSessionsList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          3,
          f,
          proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.getSpliceActive = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 2, false)
      );
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.setSpliceActive = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 2, value);
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.getSessionsList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.SessionSnapshot>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.SessionSnapshot, 3)
      );
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.setSessionsList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.addSessions = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 3, opt_value, proto.scp_cv.v1.SessionSnapshot, opt_index);
    };
    proto.scp_cv.v1.SpliceModeReply.prototype.clearSessionsList = function() {
      return this.setSessionsList([]);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.SessionSnapshot.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.SessionSnapshot.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.SessionSnapshot.toObject = function(includeInstance, msg) {
        var f, obj = {
          windowId: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          sessionId: jspb2.Message.getFieldWithDefault(msg, 2, 0),
          sourceName: jspb2.Message.getFieldWithDefault(msg, 3, ""),
          sourceType: jspb2.Message.getFieldWithDefault(msg, 4, ""),
          sourceTypeLabel: jspb2.Message.getFieldWithDefault(msg, 5, ""),
          sourceUri: jspb2.Message.getFieldWithDefault(msg, 6, ""),
          playbackState: jspb2.Message.getFieldWithDefault(msg, 7, ""),
          playbackStateLabel: jspb2.Message.getFieldWithDefault(msg, 8, ""),
          displayMode: jspb2.Message.getFieldWithDefault(msg, 9, ""),
          displayModeLabel: jspb2.Message.getFieldWithDefault(msg, 10, ""),
          targetDisplayLabel: jspb2.Message.getFieldWithDefault(msg, 11, ""),
          splicedDisplayLabel: jspb2.Message.getFieldWithDefault(msg, 12, ""),
          isSpliced: jspb2.Message.getBooleanFieldWithDefault(msg, 13, false),
          currentSlide: jspb2.Message.getFieldWithDefault(msg, 14, 0),
          totalSlides: jspb2.Message.getFieldWithDefault(msg, 15, 0),
          positionMs: jspb2.Message.getFieldWithDefault(msg, 16, 0),
          durationMs: jspb2.Message.getFieldWithDefault(msg, 17, 0),
          pendingCommand: jspb2.Message.getFieldWithDefault(msg, 18, ""),
          lastUpdatedAt: jspb2.Message.getFieldWithDefault(msg, 19, ""),
          loopEnabled: jspb2.Message.getBooleanFieldWithDefault(msg, 20, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.SessionSnapshot.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.SessionSnapshot();
      return proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setWindowId(value);
            break;
          case 2:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setSessionId(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceName(value);
            break;
          case 4:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceType(value);
            break;
          case 5:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceTypeLabel(value);
            break;
          case 6:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSourceUri(value);
            break;
          case 7:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPlaybackState(value);
            break;
          case 8:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPlaybackStateLabel(value);
            break;
          case 9:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDisplayMode(value);
            break;
          case 10:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDisplayModeLabel(value);
            break;
          case 11:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setTargetDisplayLabel(value);
            break;
          case 12:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setSplicedDisplayLabel(value);
            break;
          case 13:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsSpliced(value);
            break;
          case 14:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setCurrentSlide(value);
            break;
          case 15:
            var value = (
              /** @type {number} */
              reader.readInt32()
            );
            msg.setTotalSlides(value);
            break;
          case 16:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setPositionMs(value);
            break;
          case 17:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setDurationMs(value);
            break;
          case 18:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setPendingCommand(value);
            break;
          case 19:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setLastUpdatedAt(value);
            break;
          case 20:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setLoopEnabled(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getWindowId();
      if (f !== 0) {
        writer.writeInt32(
          1,
          f
        );
      }
      f = message.getSessionId();
      if (f !== 0) {
        writer.writeInt64(
          2,
          f
        );
      }
      f = message.getSourceName();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
      f = message.getSourceType();
      if (f.length > 0) {
        writer.writeString(
          4,
          f
        );
      }
      f = message.getSourceTypeLabel();
      if (f.length > 0) {
        writer.writeString(
          5,
          f
        );
      }
      f = message.getSourceUri();
      if (f.length > 0) {
        writer.writeString(
          6,
          f
        );
      }
      f = message.getPlaybackState();
      if (f.length > 0) {
        writer.writeString(
          7,
          f
        );
      }
      f = message.getPlaybackStateLabel();
      if (f.length > 0) {
        writer.writeString(
          8,
          f
        );
      }
      f = message.getDisplayMode();
      if (f.length > 0) {
        writer.writeString(
          9,
          f
        );
      }
      f = message.getDisplayModeLabel();
      if (f.length > 0) {
        writer.writeString(
          10,
          f
        );
      }
      f = message.getTargetDisplayLabel();
      if (f.length > 0) {
        writer.writeString(
          11,
          f
        );
      }
      f = message.getSplicedDisplayLabel();
      if (f.length > 0) {
        writer.writeString(
          12,
          f
        );
      }
      f = message.getIsSpliced();
      if (f) {
        writer.writeBool(
          13,
          f
        );
      }
      f = message.getCurrentSlide();
      if (f !== 0) {
        writer.writeInt32(
          14,
          f
        );
      }
      f = message.getTotalSlides();
      if (f !== 0) {
        writer.writeInt32(
          15,
          f
        );
      }
      f = message.getPositionMs();
      if (f !== 0) {
        writer.writeInt64(
          16,
          f
        );
      }
      f = message.getDurationMs();
      if (f !== 0) {
        writer.writeInt64(
          17,
          f
        );
      }
      f = message.getPendingCommand();
      if (f.length > 0) {
        writer.writeString(
          18,
          f
        );
      }
      f = message.getLastUpdatedAt();
      if (f.length > 0) {
        writer.writeString(
          19,
          f
        );
      }
      f = message.getLoopEnabled();
      if (f) {
        writer.writeBool(
          20,
          f
        );
      }
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getWindowId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setWindowId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSessionId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 2, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSessionId = function(value) {
      return jspb2.Message.setProto3IntField(this, 2, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSourceName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSourceName = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSourceType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 4, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSourceType = function(value) {
      return jspb2.Message.setProto3StringField(this, 4, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSourceTypeLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 5, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSourceTypeLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 5, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSourceUri = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 6, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSourceUri = function(value) {
      return jspb2.Message.setProto3StringField(this, 6, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getPlaybackState = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 7, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setPlaybackState = function(value) {
      return jspb2.Message.setProto3StringField(this, 7, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getPlaybackStateLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 8, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setPlaybackStateLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 8, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getDisplayMode = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 9, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setDisplayMode = function(value) {
      return jspb2.Message.setProto3StringField(this, 9, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getDisplayModeLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 10, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setDisplayModeLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 10, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getTargetDisplayLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 11, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setTargetDisplayLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 11, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getSplicedDisplayLabel = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 12, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setSplicedDisplayLabel = function(value) {
      return jspb2.Message.setProto3StringField(this, 12, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getIsSpliced = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 13, false)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setIsSpliced = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 13, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getCurrentSlide = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 14, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setCurrentSlide = function(value) {
      return jspb2.Message.setProto3IntField(this, 14, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getTotalSlides = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 15, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setTotalSlides = function(value) {
      return jspb2.Message.setProto3IntField(this, 15, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getPositionMs = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 16, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setPositionMs = function(value) {
      return jspb2.Message.setProto3IntField(this, 16, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getDurationMs = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 17, 0)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setDurationMs = function(value) {
      return jspb2.Message.setProto3IntField(this, 17, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getPendingCommand = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 18, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setPendingCommand = function(value) {
      return jspb2.Message.setProto3StringField(this, 18, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getLastUpdatedAt = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 19, "")
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setLastUpdatedAt = function(value) {
      return jspb2.Message.setProto3StringField(this, 19, value);
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.getLoopEnabled = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 20, false)
      );
    };
    proto.scp_cv.v1.SessionSnapshot.prototype.setLoopEnabled = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 20, value);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.repeatedFields_ = [3];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.AllSessionSnapshotsReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.AllSessionSnapshotsReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          spliceActive: jspb2.Message.getBooleanFieldWithDefault(msg, 2, false),
          sessionsList: jspb2.Message.toObjectList(
            msg.getSessionsList(),
            proto.scp_cv.v1.SessionSnapshot.toObject,
            includeInstance
          )
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.AllSessionSnapshotsReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.AllSessionSnapshotsReply();
      return proto.scp_cv.v1.AllSessionSnapshotsReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSpliceActive(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.SessionSnapshot();
            reader.readMessage(value, proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader);
            msg.addSessions(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.AllSessionSnapshotsReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getSpliceActive();
      if (f) {
        writer.writeBool(
          2,
          f
        );
      }
      f = message.getSessionsList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          3,
          f,
          proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.getSpliceActive = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 2, false)
      );
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.setSpliceActive = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 2, value);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.getSessionsList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.SessionSnapshot>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.SessionSnapshot, 3)
      );
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.setSessionsList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.addSessions = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 3, opt_value, proto.scp_cv.v1.SessionSnapshot, opt_index);
    };
    proto.scp_cv.v1.AllSessionSnapshotsReply.prototype.clearSessionsList = function() {
      return this.setSessionsList([]);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ScenarioWindowSlot.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ScenarioWindowSlot.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ScenarioWindowSlot.toObject = function(includeInstance, msg) {
        var f, obj = {
          sourceId: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          autoplay: jspb2.Message.getBooleanFieldWithDefault(msg, 2, false),
          resume: jspb2.Message.getBooleanFieldWithDefault(msg, 3, false)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ScenarioWindowSlot();
      return proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setSourceId(value);
            break;
          case 2:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setAutoplay(value);
            break;
          case 3:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setResume(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSourceId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
      f = message.getAutoplay();
      if (f) {
        writer.writeBool(
          2,
          f
        );
      }
      f = message.getResume();
      if (f) {
        writer.writeBool(
          3,
          f
        );
      }
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.getSourceId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.setSourceId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.getAutoplay = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 2, false)
      );
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.setAutoplay = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 2, value);
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.getResume = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 3, false)
      );
    };
    proto.scp_cv.v1.ScenarioWindowSlot.prototype.setResume = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 3, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ScenarioDetail.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ScenarioDetail.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ScenarioDetail.toObject = function(includeInstance, msg) {
        var f, obj = {
          name: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          description: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          isSpliceMode: jspb2.Message.getBooleanFieldWithDefault(msg, 3, false),
          window1: (f = msg.getWindow1()) && proto.scp_cv.v1.ScenarioWindowSlot.toObject(includeInstance, f),
          window2: (f = msg.getWindow2()) && proto.scp_cv.v1.ScenarioWindowSlot.toObject(includeInstance, f)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ScenarioDetail.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ScenarioDetail();
      return proto.scp_cv.v1.ScenarioDetail.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ScenarioDetail.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDescription(value);
            break;
          case 3:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsSpliceMode(value);
            break;
          case 4:
            var value = new proto.scp_cv.v1.ScenarioWindowSlot();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader);
            msg.setWindow1(value);
            break;
          case 5:
            var value = new proto.scp_cv.v1.ScenarioWindowSlot();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader);
            msg.setWindow2(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ScenarioDetail.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ScenarioDetail.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getDescription();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getIsSpliceMode();
      if (f) {
        writer.writeBool(
          3,
          f
        );
      }
      f = message.getWindow1();
      if (f != null) {
        writer.writeMessage(
          4,
          f,
          proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter
        );
      }
      f = message.getWindow2();
      if (f != null) {
        writer.writeMessage(
          5,
          f,
          proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.getDescription = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.setDescription = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.getIsSpliceMode = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 3, false)
      );
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.setIsSpliceMode = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 3, value);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.getWindow1 = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioWindowSlot} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioWindowSlot, 4)
      );
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.setWindow1 = function(value) {
      return jspb2.Message.setWrapperField(this, 4, value);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.clearWindow1 = function() {
      return this.setWindow1(void 0);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.hasWindow1 = function() {
      return jspb2.Message.getField(this, 4) != null;
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.getWindow2 = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioWindowSlot} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioWindowSlot, 5)
      );
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.setWindow2 = function(value) {
      return jspb2.Message.setWrapperField(this, 5, value);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.clearWindow2 = function() {
      return this.setWindow2(void 0);
    };
    proto.scp_cv.v1.ScenarioDetail.prototype.hasWindow2 = function() {
      return jspb2.Message.getField(this, 5) != null;
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ScenarioItem.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ScenarioItem.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ScenarioItem.toObject = function(includeInstance, msg) {
        var f, obj = {
          id: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          name: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          description: jspb2.Message.getFieldWithDefault(msg, 3, ""),
          isSpliceMode: jspb2.Message.getBooleanFieldWithDefault(msg, 4, false),
          window1: (f = msg.getWindow1()) && proto.scp_cv.v1.ScenarioWindowSlot.toObject(includeInstance, f),
          window2: (f = msg.getWindow2()) && proto.scp_cv.v1.ScenarioWindowSlot.toObject(includeInstance, f),
          createdAt: jspb2.Message.getFieldWithDefault(msg, 7, ""),
          updatedAt: jspb2.Message.getFieldWithDefault(msg, 8, "")
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ScenarioItem.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ScenarioItem();
      return proto.scp_cv.v1.ScenarioItem.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ScenarioItem.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setId(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setName(value);
            break;
          case 3:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setDescription(value);
            break;
          case 4:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setIsSpliceMode(value);
            break;
          case 5:
            var value = new proto.scp_cv.v1.ScenarioWindowSlot();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader);
            msg.setWindow1(value);
            break;
          case 6:
            var value = new proto.scp_cv.v1.ScenarioWindowSlot();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioWindowSlot.deserializeBinaryFromReader);
            msg.setWindow2(value);
            break;
          case 7:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setCreatedAt(value);
            break;
          case 8:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setUpdatedAt(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ScenarioItem.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ScenarioItem.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ScenarioItem.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
      f = message.getName();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getDescription();
      if (f.length > 0) {
        writer.writeString(
          3,
          f
        );
      }
      f = message.getIsSpliceMode();
      if (f) {
        writer.writeBool(
          4,
          f
        );
      }
      f = message.getWindow1();
      if (f != null) {
        writer.writeMessage(
          5,
          f,
          proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter
        );
      }
      f = message.getWindow2();
      if (f != null) {
        writer.writeMessage(
          6,
          f,
          proto.scp_cv.v1.ScenarioWindowSlot.serializeBinaryToWriter
        );
      }
      f = message.getCreatedAt();
      if (f.length > 0) {
        writer.writeString(
          7,
          f
        );
      }
      f = message.getUpdatedAt();
      if (f.length > 0) {
        writer.writeString(
          8,
          f
        );
      }
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getName = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setName = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getDescription = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 3, "")
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setDescription = function(value) {
      return jspb2.Message.setProto3StringField(this, 3, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getIsSpliceMode = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 4, false)
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setIsSpliceMode = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 4, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getWindow1 = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioWindowSlot} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioWindowSlot, 5)
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setWindow1 = function(value) {
      return jspb2.Message.setWrapperField(this, 5, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.clearWindow1 = function() {
      return this.setWindow1(void 0);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.hasWindow1 = function() {
      return jspb2.Message.getField(this, 5) != null;
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getWindow2 = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioWindowSlot} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioWindowSlot, 6)
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setWindow2 = function(value) {
      return jspb2.Message.setWrapperField(this, 6, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.clearWindow2 = function() {
      return this.setWindow2(void 0);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.hasWindow2 = function() {
      return jspb2.Message.getField(this, 6) != null;
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getCreatedAt = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 7, "")
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setCreatedAt = function(value) {
      return jspb2.Message.setProto3StringField(this, 7, value);
    };
    proto.scp_cv.v1.ScenarioItem.prototype.getUpdatedAt = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 8, "")
      );
    };
    proto.scp_cv.v1.ScenarioItem.prototype.setUpdatedAt = function(value) {
      return jspb2.Message.setProto3StringField(this, 8, value);
    };
    proto.scp_cv.v1.ListScenariosReply.repeatedFields_ = [2];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ListScenariosReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ListScenariosReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ListScenariosReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          scenariosList: jspb2.Message.toObjectList(
            msg.getScenariosList(),
            proto.scp_cv.v1.ScenarioItem.toObject,
            includeInstance
          )
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ListScenariosReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ListScenariosReply();
      return proto.scp_cv.v1.ListScenariosReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ListScenariosReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = new proto.scp_cv.v1.ScenarioItem();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioItem.deserializeBinaryFromReader);
            msg.addScenarios(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ListScenariosReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ListScenariosReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getScenariosList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          2,
          f,
          proto.scp_cv.v1.ScenarioItem.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.getScenariosList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.ScenarioItem>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.ScenarioItem, 2)
      );
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.setScenariosList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 2, value);
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.addScenarios = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 2, opt_value, proto.scp_cv.v1.ScenarioItem, opt_index);
    };
    proto.scp_cv.v1.ListScenariosReply.prototype.clearScenariosList = function() {
      return this.setScenariosList([]);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.UpdateScenarioRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.UpdateScenarioRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.UpdateScenarioRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          scenarioId: jspb2.Message.getFieldWithDefault(msg, 1, 0),
          detail: (f = msg.getDetail()) && proto.scp_cv.v1.ScenarioDetail.toObject(includeInstance, f)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.UpdateScenarioRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.UpdateScenarioRequest();
      return proto.scp_cv.v1.UpdateScenarioRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.UpdateScenarioRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setScenarioId(value);
            break;
          case 2:
            var value = new proto.scp_cv.v1.ScenarioDetail();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioDetail.deserializeBinaryFromReader);
            msg.setDetail(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.UpdateScenarioRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.UpdateScenarioRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getScenarioId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
      f = message.getDetail();
      if (f != null) {
        writer.writeMessage(
          2,
          f,
          proto.scp_cv.v1.ScenarioDetail.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.getScenarioId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.setScenarioId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.getDetail = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioDetail} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioDetail, 2)
      );
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.setDetail = function(value) {
      return jspb2.Message.setWrapperField(this, 2, value);
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.clearDetail = function() {
      return this.setDetail(void 0);
    };
    proto.scp_cv.v1.UpdateScenarioRequest.prototype.hasDetail = function() {
      return jspb2.Message.getField(this, 2) != null;
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.DeleteScenarioRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.DeleteScenarioRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.DeleteScenarioRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          scenarioId: jspb2.Message.getFieldWithDefault(msg, 1, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.DeleteScenarioRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.DeleteScenarioRequest();
      return proto.scp_cv.v1.DeleteScenarioRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.DeleteScenarioRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setScenarioId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.DeleteScenarioRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.DeleteScenarioRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.DeleteScenarioRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getScenarioId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.DeleteScenarioRequest.prototype.getScenarioId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.DeleteScenarioRequest.prototype.setScenarioId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ActivateScenarioRequest.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ActivateScenarioRequest.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ActivateScenarioRequest.toObject = function(includeInstance, msg) {
        var f, obj = {
          scenarioId: jspb2.Message.getFieldWithDefault(msg, 1, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ActivateScenarioRequest.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ActivateScenarioRequest();
      return proto.scp_cv.v1.ActivateScenarioRequest.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ActivateScenarioRequest.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setScenarioId(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ActivateScenarioRequest.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ActivateScenarioRequest.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ActivateScenarioRequest.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getScenarioId();
      if (f !== 0) {
        writer.writeInt64(
          1,
          f
        );
      }
    };
    proto.scp_cv.v1.ActivateScenarioRequest.prototype.getScenarioId = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 1, 0)
      );
    };
    proto.scp_cv.v1.ActivateScenarioRequest.prototype.setScenarioId = function(value) {
      return jspb2.Message.setProto3IntField(this, 1, value);
    };
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ScenarioReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ScenarioReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ScenarioReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          message: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          scenario: (f = msg.getScenario()) && proto.scp_cv.v1.ScenarioItem.toObject(includeInstance, f)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ScenarioReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ScenarioReply();
      return proto.scp_cv.v1.ScenarioReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ScenarioReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setMessage(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.ScenarioItem();
            reader.readMessage(value, proto.scp_cv.v1.ScenarioItem.deserializeBinaryFromReader);
            msg.setScenario(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ScenarioReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ScenarioReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ScenarioReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getMessage();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getScenario();
      if (f != null) {
        writer.writeMessage(
          3,
          f,
          proto.scp_cv.v1.ScenarioItem.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.ScenarioReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.ScenarioReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.ScenarioReply.prototype.getMessage = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.ScenarioReply.prototype.setMessage = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.ScenarioReply.prototype.getScenario = function() {
      return (
        /** @type{?proto.scp_cv.v1.ScenarioItem} */
        jspb2.Message.getWrapperField(this, proto.scp_cv.v1.ScenarioItem, 3)
      );
    };
    proto.scp_cv.v1.ScenarioReply.prototype.setScenario = function(value) {
      return jspb2.Message.setWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.ScenarioReply.prototype.clearScenario = function() {
      return this.setScenario(void 0);
    };
    proto.scp_cv.v1.ScenarioReply.prototype.hasScenario = function() {
      return jspb2.Message.getField(this, 3) != null;
    };
    proto.scp_cv.v1.ActivateScenarioReply.repeatedFields_ = [3];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.ActivateScenarioReply.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.ActivateScenarioReply.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.ActivateScenarioReply.toObject = function(includeInstance, msg) {
        var f, obj = {
          success: jspb2.Message.getBooleanFieldWithDefault(msg, 1, false),
          message: jspb2.Message.getFieldWithDefault(msg, 2, ""),
          sessionsList: jspb2.Message.toObjectList(
            msg.getSessionsList(),
            proto.scp_cv.v1.SessionSnapshot.toObject,
            includeInstance
          )
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.ActivateScenarioReply.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.ActivateScenarioReply();
      return proto.scp_cv.v1.ActivateScenarioReply.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.ActivateScenarioReply.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {boolean} */
              reader.readBool()
            );
            msg.setSuccess(value);
            break;
          case 2:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setMessage(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.SessionSnapshot();
            reader.readMessage(value, proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader);
            msg.addSessions(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.ActivateScenarioReply.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.ActivateScenarioReply.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getSuccess();
      if (f) {
        writer.writeBool(
          1,
          f
        );
      }
      f = message.getMessage();
      if (f.length > 0) {
        writer.writeString(
          2,
          f
        );
      }
      f = message.getSessionsList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          3,
          f,
          proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter
        );
      }
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.getSuccess = function() {
      return (
        /** @type {boolean} */
        jspb2.Message.getBooleanFieldWithDefault(this, 1, false)
      );
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.setSuccess = function(value) {
      return jspb2.Message.setProto3BooleanField(this, 1, value);
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.getMessage = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 2, "")
      );
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.setMessage = function(value) {
      return jspb2.Message.setProto3StringField(this, 2, value);
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.getSessionsList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.SessionSnapshot>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.SessionSnapshot, 3)
      );
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.setSessionsList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.addSessions = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 3, opt_value, proto.scp_cv.v1.SessionSnapshot, opt_index);
    };
    proto.scp_cv.v1.ActivateScenarioReply.prototype.clearSessionsList = function() {
      return this.setSessionsList([]);
    };
    proto.scp_cv.v1.PlaybackStateEvent.repeatedFields_ = [3];
    if (jspb2.Message.GENERATE_TO_OBJECT) {
      proto.scp_cv.v1.PlaybackStateEvent.prototype.toObject = function(opt_includeInstance) {
        return proto.scp_cv.v1.PlaybackStateEvent.toObject(opt_includeInstance, this);
      };
      proto.scp_cv.v1.PlaybackStateEvent.toObject = function(includeInstance, msg) {
        var f, obj = {
          eventType: jspb2.Message.getFieldWithDefault(msg, 1, ""),
          sequence: jspb2.Message.getFieldWithDefault(msg, 2, 0),
          sessionsList: jspb2.Message.toObjectList(
            msg.getSessionsList(),
            proto.scp_cv.v1.SessionSnapshot.toObject,
            includeInstance
          ),
          timestamp: jspb2.Message.getFloatingPointFieldWithDefault(msg, 4, 0)
        };
        if (includeInstance) {
          obj.$jspbMessageInstance = msg;
        }
        return obj;
      };
    }
    proto.scp_cv.v1.PlaybackStateEvent.deserializeBinary = function(bytes) {
      var reader = new jspb2.BinaryReader(bytes);
      var msg = new proto.scp_cv.v1.PlaybackStateEvent();
      return proto.scp_cv.v1.PlaybackStateEvent.deserializeBinaryFromReader(msg, reader);
    };
    proto.scp_cv.v1.PlaybackStateEvent.deserializeBinaryFromReader = function(msg, reader) {
      while (reader.nextField()) {
        if (reader.isEndGroup()) {
          break;
        }
        var field = reader.getFieldNumber();
        switch (field) {
          case 1:
            var value = (
              /** @type {string} */
              reader.readStringRequireUtf8()
            );
            msg.setEventType(value);
            break;
          case 2:
            var value = (
              /** @type {number} */
              reader.readInt64()
            );
            msg.setSequence(value);
            break;
          case 3:
            var value = new proto.scp_cv.v1.SessionSnapshot();
            reader.readMessage(value, proto.scp_cv.v1.SessionSnapshot.deserializeBinaryFromReader);
            msg.addSessions(value);
            break;
          case 4:
            var value = (
              /** @type {number} */
              reader.readDouble()
            );
            msg.setTimestamp(value);
            break;
          default:
            reader.skipField();
            break;
        }
      }
      return msg;
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.serializeBinary = function() {
      var writer = new jspb2.BinaryWriter();
      proto.scp_cv.v1.PlaybackStateEvent.serializeBinaryToWriter(this, writer);
      return writer.getResultBuffer();
    };
    proto.scp_cv.v1.PlaybackStateEvent.serializeBinaryToWriter = function(message, writer) {
      var f = void 0;
      f = message.getEventType();
      if (f.length > 0) {
        writer.writeString(
          1,
          f
        );
      }
      f = message.getSequence();
      if (f !== 0) {
        writer.writeInt64(
          2,
          f
        );
      }
      f = message.getSessionsList();
      if (f.length > 0) {
        writer.writeRepeatedMessage(
          3,
          f,
          proto.scp_cv.v1.SessionSnapshot.serializeBinaryToWriter
        );
      }
      f = message.getTimestamp();
      if (f !== 0) {
        writer.writeDouble(
          4,
          f
        );
      }
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.getEventType = function() {
      return (
        /** @type {string} */
        jspb2.Message.getFieldWithDefault(this, 1, "")
      );
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.setEventType = function(value) {
      return jspb2.Message.setProto3StringField(this, 1, value);
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.getSequence = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFieldWithDefault(this, 2, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.setSequence = function(value) {
      return jspb2.Message.setProto3IntField(this, 2, value);
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.getSessionsList = function() {
      return (
        /** @type{!Array<!proto.scp_cv.v1.SessionSnapshot>} */
        jspb2.Message.getRepeatedWrapperField(this, proto.scp_cv.v1.SessionSnapshot, 3)
      );
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.setSessionsList = function(value) {
      return jspb2.Message.setRepeatedWrapperField(this, 3, value);
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.addSessions = function(opt_value, opt_index) {
      return jspb2.Message.addToRepeatedWrapperField(this, 3, opt_value, proto.scp_cv.v1.SessionSnapshot, opt_index);
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.clearSessionsList = function() {
      return this.setSessionsList([]);
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.getTimestamp = function() {
      return (
        /** @type {number} */
        jspb2.Message.getFloatingPointFieldWithDefault(this, 4, 0)
      );
    };
    proto.scp_cv.v1.PlaybackStateEvent.prototype.setTimestamp = function(value) {
      return jspb2.Message.setProto3FloatField(this, 4, value);
    };
    proto.scp_cv.v1.SourceType = {
      SOURCE_UNKNOWN: 0,
      SOURCE_PPT: 1,
      SOURCE_VIDEO: 2,
      SOURCE_AUDIO: 3,
      SOURCE_IMAGE: 4,
      SOURCE_WEB: 5,
      SOURCE_CUSTOM_STREAM: 6,
      SOURCE_RTSP_STREAM: 7,
      SOURCE_SRT_STREAM: 8
    };
    proto.scp_cv.v1.PlaybackAction = {
      ACTION_UNKNOWN: 0,
      ACTION_PLAY: 1,
      ACTION_PAUSE: 2,
      ACTION_STOP: 3
    };
    proto.scp_cv.v1.NavigateAction = {
      NAV_UNKNOWN: 0,
      NAV_NEXT: 1,
      NAV_PREV: 2,
      NAV_GOTO: 3,
      NAV_SEEK: 4
    };
    goog2.object.extend(exports2, proto.scp_cv.v1);
  }
});

// static/js/grpc-generated/scp_cv/v1/control_grpc_web_pb.js
var require_control_grpc_web_pb = __commonJS({
  "static/js/grpc-generated/scp_cv/v1/control_grpc_web_pb.js"(exports2, module2) {
    var grpc = {};
    grpc.web = require_grpc_web();
    var proto2 = {};
    proto2.scp_cv = {};
    proto2.scp_cv.v1 = require_control_pb();
    proto2.scp_cv.v1.PlaybackControlServiceClient = function(hostname, credentials, options) {
      if (!options) options = {};
      options.format = "text";
      this.client_ = new grpc.web.GrpcWebClientBase(options);
      this.hostname_ = hostname.replace(/\/+$/, "");
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient = function(hostname, credentials, options) {
      if (!options) options = {};
      options.format = "text";
      this.client_ = new grpc.web.GrpcWebClientBase(options);
      this.hostname_ = hostname.replace(/\/+$/, "");
    };
    var methodDescriptor_PlaybackControlService_OpenSource = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/OpenSource",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.OpenSourceRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.OpenSourceRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.openSource = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/OpenSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_OpenSource,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.openSource = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/OpenSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_OpenSource
      );
    };
    var methodDescriptor_PlaybackControlService_CloseSource = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/CloseSource",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.CloseSourceRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.CloseSourceRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.closeSource = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/CloseSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_CloseSource,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.closeSource = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/CloseSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_CloseSource
      );
    };
    var methodDescriptor_PlaybackControlService_ControlPlayback = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ControlPlayback",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.ControlPlaybackRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.ControlPlaybackRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.controlPlayback = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ControlPlayback",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ControlPlayback,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.controlPlayback = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ControlPlayback",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ControlPlayback
      );
    };
    var methodDescriptor_PlaybackControlService_NavigateContent = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/NavigateContent",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.NavigateContentRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.NavigateContentRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.navigateContent = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/NavigateContent",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_NavigateContent,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.navigateContent = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/NavigateContent",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_NavigateContent
      );
    };
    var methodDescriptor_PlaybackControlService_GetRuntimeStatus = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/GetRuntimeStatus",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.WindowRequest,
      proto2.scp_cv.v1.RuntimeStatusReply,
      /**
       * @param {!proto.scp_cv.v1.WindowRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.RuntimeStatusReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.getRuntimeStatus = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetRuntimeStatus",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetRuntimeStatus,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.getRuntimeStatus = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetRuntimeStatus",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetRuntimeStatus
      );
    };
    var methodDescriptor_PlaybackControlService_GetPlaybackState = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/GetPlaybackState",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.WindowRequest,
      proto2.scp_cv.v1.PlaybackStateReply,
      /**
       * @param {!proto.scp_cv.v1.WindowRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.PlaybackStateReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.getPlaybackState = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetPlaybackState",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetPlaybackState,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.getPlaybackState = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetPlaybackState",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetPlaybackState
      );
    };
    var methodDescriptor_PlaybackControlService_ListDisplayTargets = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ListDisplayTargets",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.DisplayTargetsReply,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.DisplayTargetsReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.listDisplayTargets = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListDisplayTargets",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListDisplayTargets,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.listDisplayTargets = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListDisplayTargets",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListDisplayTargets
      );
    };
    var methodDescriptor_PlaybackControlService_SelectDisplayTarget = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/SelectDisplayTarget",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.SelectDisplayTargetRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.SelectDisplayTargetRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.selectDisplayTarget = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/SelectDisplayTarget",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_SelectDisplayTarget,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.selectDisplayTarget = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/SelectDisplayTarget",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_SelectDisplayTarget
      );
    };
    var methodDescriptor_PlaybackControlService_ListSources = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ListSources",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.ListSourcesRequest,
      proto2.scp_cv.v1.ListSourcesReply,
      /**
       * @param {!proto.scp_cv.v1.ListSourcesRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.ListSourcesReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.listSources = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListSources",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListSources,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.listSources = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListSources",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListSources
      );
    };
    var methodDescriptor_PlaybackControlService_AddLocalPathSource = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/AddLocalPathSource",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.AddLocalPathSourceRequest,
      proto2.scp_cv.v1.SourceReply,
      /**
       * @param {!proto.scp_cv.v1.AddLocalPathSourceRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.SourceReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.addLocalPathSource = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/AddLocalPathSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_AddLocalPathSource,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.addLocalPathSource = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/AddLocalPathSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_AddLocalPathSource
      );
    };
    var methodDescriptor_PlaybackControlService_AddWebUrlSource = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/AddWebUrlSource",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.AddWebUrlSourceRequest,
      proto2.scp_cv.v1.SourceReply,
      /**
       * @param {!proto.scp_cv.v1.AddWebUrlSourceRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.SourceReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.addWebUrlSource = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/AddWebUrlSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_AddWebUrlSource,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.addWebUrlSource = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/AddWebUrlSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_AddWebUrlSource
      );
    };
    var methodDescriptor_PlaybackControlService_DeleteSource = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/DeleteSource",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.DeleteSourceRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.DeleteSourceRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.deleteSource = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/DeleteSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_DeleteSource,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.deleteSource = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/DeleteSource",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_DeleteSource
      );
    };
    var methodDescriptor_PlaybackControlService_ToggleLoop = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ToggleLoop",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.ToggleLoopRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.ToggleLoopRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.toggleLoop = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ToggleLoop",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ToggleLoop,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.toggleLoop = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ToggleLoop",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ToggleLoop
      );
    };
    var methodDescriptor_PlaybackControlService_SetSpliceMode = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/SetSpliceMode",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.SetSpliceModeRequest,
      proto2.scp_cv.v1.SpliceModeReply,
      /**
       * @param {!proto.scp_cv.v1.SetSpliceModeRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.SpliceModeReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.setSpliceMode = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/SetSpliceMode",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_SetSpliceMode,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.setSpliceMode = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/SetSpliceMode",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_SetSpliceMode
      );
    };
    var methodDescriptor_PlaybackControlService_ShowWindowIds = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ShowWindowIds",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.showWindowIds = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ShowWindowIds",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ShowWindowIds,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.showWindowIds = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ShowWindowIds",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ShowWindowIds
      );
    };
    var methodDescriptor_PlaybackControlService_GetAllSessionSnapshots = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/GetAllSessionSnapshots",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.AllSessionSnapshotsReply,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.AllSessionSnapshotsReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.getAllSessionSnapshots = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetAllSessionSnapshots",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetAllSessionSnapshots,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.getAllSessionSnapshots = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/GetAllSessionSnapshots",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_GetAllSessionSnapshots
      );
    };
    var methodDescriptor_PlaybackControlService_WatchPlaybackState = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/WatchPlaybackState",
      grpc.web.MethodType.SERVER_STREAMING,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.PlaybackStateEvent,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.PlaybackStateEvent.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.watchPlaybackState = function(request, metadata) {
      return this.client_.serverStreaming(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/WatchPlaybackState",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_WatchPlaybackState
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.watchPlaybackState = function(request, metadata) {
      return this.client_.serverStreaming(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/WatchPlaybackState",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_WatchPlaybackState
      );
    };
    var methodDescriptor_PlaybackControlService_ListScenarios = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ListScenarios",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.ListScenariosReply,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.ListScenariosReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.listScenarios = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListScenarios",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListScenarios,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.listScenarios = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ListScenarios",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ListScenarios
      );
    };
    var methodDescriptor_PlaybackControlService_CreateScenario = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/CreateScenario",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.ScenarioDetail,
      proto2.scp_cv.v1.ScenarioReply,
      /**
       * @param {!proto.scp_cv.v1.ScenarioDetail} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.ScenarioReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.createScenario = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/CreateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_CreateScenario,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.createScenario = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/CreateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_CreateScenario
      );
    };
    var methodDescriptor_PlaybackControlService_UpdateScenario = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/UpdateScenario",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.UpdateScenarioRequest,
      proto2.scp_cv.v1.ScenarioReply,
      /**
       * @param {!proto.scp_cv.v1.UpdateScenarioRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.ScenarioReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.updateScenario = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/UpdateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_UpdateScenario,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.updateScenario = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/UpdateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_UpdateScenario
      );
    };
    var methodDescriptor_PlaybackControlService_DeleteScenario = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/DeleteScenario",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.DeleteScenarioRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.DeleteScenarioRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.deleteScenario = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/DeleteScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_DeleteScenario,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.deleteScenario = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/DeleteScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_DeleteScenario
      );
    };
    var methodDescriptor_PlaybackControlService_ActivateScenario = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/ActivateScenario",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.ActivateScenarioRequest,
      proto2.scp_cv.v1.ActivateScenarioReply,
      /**
       * @param {!proto.scp_cv.v1.ActivateScenarioRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.ActivateScenarioReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.activateScenario = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ActivateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ActivateScenario,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.activateScenario = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/ActivateScenario",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_ActivateScenario
      );
    };
    var methodDescriptor_PlaybackControlService_StopCurrentContent = new grpc.web.MethodDescriptor(
      "/scp_cv.v1.PlaybackControlService/StopCurrentContent",
      grpc.web.MethodType.UNARY,
      proto2.scp_cv.v1.EmptyRequest,
      proto2.scp_cv.v1.OperationReply,
      /**
       * @param {!proto.scp_cv.v1.EmptyRequest} request
       * @return {!Uint8Array}
       */
      function(request) {
        return request.serializeBinary();
      },
      proto2.scp_cv.v1.OperationReply.deserializeBinary
    );
    proto2.scp_cv.v1.PlaybackControlServiceClient.prototype.stopCurrentContent = function(request, metadata, callback) {
      return this.client_.rpcCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/StopCurrentContent",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_StopCurrentContent,
        callback
      );
    };
    proto2.scp_cv.v1.PlaybackControlServicePromiseClient.prototype.stopCurrentContent = function(request, metadata) {
      return this.client_.unaryCall(
        this.hostname_ + "/scp_cv.v1.PlaybackControlService/StopCurrentContent",
        request,
        metadata || {},
        methodDescriptor_PlaybackControlService_StopCurrentContent
      );
    };
    module2.exports = proto2.scp_cv.v1;
  }
});

// static/js/grpc-client.js
var {
  PlaybackControlServiceClient
} = require_control_grpc_web_pb();
var {
  EmptyRequest,
  WindowRequest,
  OpenSourceRequest,
  CloseSourceRequest,
  ControlPlaybackRequest,
  NavigateContentRequest,
  SelectDisplayTargetRequest,
  ListSourcesRequest,
  AddLocalPathSourceRequest,
  AddWebUrlSourceRequest,
  DeleteSourceRequest,
  ToggleLoopRequest,
  SetSpliceModeRequest,
  ScenarioDetail,
  ScenarioWindowSlot,
  UpdateScenarioRequest,
  DeleteScenarioRequest,
  ActivateScenarioRequest
} = require_control_pb();
var GRPC_WEB_PROXY_URL = typeof window !== "undefined" && window.GRPC_WEB_PROXY_URL || "http://localhost:8081";
var grpcClient = new PlaybackControlServiceClient(GRPC_WEB_PROXY_URL);
var PLAYBACK_ACTIONS = {
  play: 1,
  // ACTION_PLAY
  pause: 2,
  // ACTION_PAUSE
  stop: 3
  // ACTION_STOP
};
var NAVIGATE_ACTIONS = {
  next: 1,
  // NAV_NEXT
  prev: 2,
  // NAV_PREV
  goto: 3,
  // NAV_GOTO
  seek: 4
  // NAV_SEEK
};
function unaryCall(rpcName, rpcMethod, requestMessage) {
  return new Promise((resolve, reject) => {
    rpcMethod.call(grpcClient, requestMessage, {}, (grpcError, response) => {
      if (grpcError) {
        const errorDetail = `gRPC ${rpcName} \u5931\u8D25: code=${grpcError.code}, message=${grpcError.message}`;
        reject(new Error(errorDetail));
        return;
      }
      resolve(response.toObject());
    });
  });
}
function listSources(sourceType) {
  const request = new ListSourcesRequest();
  request.setSourceType(sourceType);
  return unaryCall(
    "ListSources",
    grpcClient.listSources,
    request
  );
}
function addLocalPathSource(path, name, sourceType) {
  const request = new AddLocalPathSourceRequest();
  request.setPath(path);
  request.setName(name);
  request.setSourceType(sourceType);
  return unaryCall(
    "AddLocalPathSource",
    grpcClient.addLocalPathSource,
    request
  );
}
function addWebUrlSource(url, name) {
  const request = new AddWebUrlSourceRequest();
  request.setUrl(url);
  request.setName(name);
  return unaryCall(
    "AddWebUrlSource",
    grpcClient.addWebUrlSource,
    request
  );
}
function deleteSource(mediaSourceId) {
  const request = new DeleteSourceRequest();
  request.setMediaSourceId(mediaSourceId);
  return unaryCall(
    "DeleteSource",
    grpcClient.deleteSource,
    request
  );
}
function openSource(windowId, mediaSourceId, autoplay) {
  const request = new OpenSourceRequest();
  request.setWindowId(windowId);
  request.setMediaSourceId(mediaSourceId);
  request.setAutoplay(autoplay);
  return unaryCall(
    "OpenSource",
    grpcClient.openSource,
    request
  );
}
function closeSource(windowId) {
  const request = new CloseSourceRequest();
  request.setWindowId(windowId);
  return unaryCall(
    "CloseSource",
    grpcClient.closeSource,
    request
  );
}
function controlPlayback(windowId, action) {
  const actionEnum = PLAYBACK_ACTIONS[action];
  if (actionEnum === void 0) {
    return Promise.reject(
      new Error(`\u65E0\u6548\u7684\u64AD\u653E\u52A8\u4F5C: "${action}"\uFF0C\u53EF\u9009\u503C: play, pause, stop`)
    );
  }
  const request = new ControlPlaybackRequest();
  request.setWindowId(windowId);
  request.setAction(actionEnum);
  return unaryCall(
    "ControlPlayback",
    grpcClient.controlPlayback,
    request
  );
}
function navigateContent(windowId, action, targetIndex = 0, positionMs = 0) {
  const actionEnum = NAVIGATE_ACTIONS[action];
  if (actionEnum === void 0) {
    return Promise.reject(
      new Error(`\u65E0\u6548\u7684\u5BFC\u822A\u52A8\u4F5C: "${action}"\uFF0C\u53EF\u9009\u503C: next, prev, goto, seek`)
    );
  }
  const request = new NavigateContentRequest();
  request.setWindowId(windowId);
  request.setAction(actionEnum);
  request.setTargetIndex(targetIndex);
  request.setPositionMs(positionMs);
  return unaryCall(
    "NavigateContent",
    grpcClient.navigateContent,
    request
  );
}
function toggleLoop(windowId, enabled) {
  const request = new ToggleLoopRequest();
  request.setWindowId(windowId);
  request.setEnabled(enabled);
  return unaryCall(
    "ToggleLoop",
    grpcClient.toggleLoop,
    request
  );
}
function setSpliceMode(enabled) {
  const request = new SetSpliceModeRequest();
  request.setEnabled(enabled);
  return unaryCall(
    "SetSpliceMode",
    grpcClient.setSpliceMode,
    request
  );
}
function showWindowIds() {
  const request = new EmptyRequest();
  return unaryCall(
    "ShowWindowIds",
    grpcClient.showWindowIds,
    request
  );
}
function getRuntimeStatus(windowId) {
  const request = new WindowRequest();
  request.setWindowId(windowId);
  return unaryCall(
    "GetRuntimeStatus",
    grpcClient.getRuntimeStatus,
    request
  );
}
function getPlaybackState(windowId) {
  const request = new WindowRequest();
  request.setWindowId(windowId);
  return unaryCall(
    "GetPlaybackState",
    grpcClient.getPlaybackState,
    request
  );
}
function getAllSessionSnapshots() {
  const request = new EmptyRequest();
  return unaryCall(
    "GetAllSessionSnapshots",
    grpcClient.getAllSessionSnapshots,
    request
  );
}
function listDisplayTargets() {
  const request = new EmptyRequest();
  return unaryCall(
    "ListDisplayTargets",
    grpcClient.listDisplayTargets,
    request
  );
}
function selectDisplayTarget(windowId, displayMode, targetLabel) {
  const request = new SelectDisplayTargetRequest();
  request.setWindowId(windowId);
  request.setDisplayMode(displayMode);
  request.setTargetLabel(targetLabel);
  return unaryCall(
    "SelectDisplayTarget",
    grpcClient.selectDisplayTarget,
    request
  );
}
function stopCurrentContent() {
  const request = new EmptyRequest();
  return unaryCall(
    "StopCurrentContent",
    grpcClient.stopCurrentContent,
    request
  );
}
function buildWindowSlot(windowConfig) {
  const slot = new ScenarioWindowSlot();
  slot.setSourceId(windowConfig.sourceId);
  slot.setAutoplay(windowConfig.autoplay);
  slot.setResume(windowConfig.resume);
  return slot;
}
function buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config) {
  const detail = new ScenarioDetail();
  detail.setName(name);
  detail.setDescription(description);
  detail.setIsSpliceMode(isSpliceMode);
  detail.setWindow1(buildWindowSlot(window1Config));
  detail.setWindow2(buildWindowSlot(window2Config));
  return detail;
}
function listScenarios() {
  const request = new EmptyRequest();
  return unaryCall(
    "ListScenarios",
    grpcClient.listScenarios,
    request
  );
}
function createScenario(name, description, isSpliceMode, window1Config, window2Config) {
  const request = buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config);
  return unaryCall(
    "CreateScenario",
    grpcClient.createScenario,
    request
  );
}
function updateScenario(scenarioId, name, description, isSpliceMode, window1Config, window2Config) {
  const request = new UpdateScenarioRequest();
  request.setScenarioId(scenarioId);
  request.setDetail(buildScenarioDetail(name, description, isSpliceMode, window1Config, window2Config));
  return unaryCall(
    "UpdateScenario",
    grpcClient.updateScenario,
    request
  );
}
function deleteScenario(scenarioId) {
  const request = new DeleteScenarioRequest();
  request.setScenarioId(scenarioId);
  return unaryCall(
    "DeleteScenario",
    grpcClient.deleteScenario,
    request
  );
}
function activateScenario(scenarioId) {
  const request = new ActivateScenarioRequest();
  request.setScenarioId(scenarioId);
  return unaryCall(
    "ActivateScenario",
    grpcClient.activateScenario,
    request
  );
}
function watchPlaybackState(onEvent, onError, onEnd) {
  const request = new EmptyRequest();
  const stream = grpcClient.watchPlaybackState(request, {});
  stream.on("data", (response) => {
    onEvent(response.toObject());
  });
  stream.on("error", (streamError) => {
    if (onError) {
      onError(streamError);
    }
  });
  stream.on("end", () => {
    if (onEnd) {
      onEnd();
    }
  });
  return () => {
    stream.cancel();
  };
}
export {
  activateScenario,
  addLocalPathSource,
  addWebUrlSource,
  closeSource,
  controlPlayback,
  createScenario,
  deleteScenario,
  deleteSource,
  getAllSessionSnapshots,
  getPlaybackState,
  getRuntimeStatus,
  listDisplayTargets,
  listScenarios,
  listSources,
  navigateContent,
  openSource,
  selectDisplayTarget,
  setSpliceMode,
  showWindowIds,
  stopCurrentContent,
  toggleLoop,
  updateScenario,
  watchPlaybackState
};
//# sourceMappingURL=grpc-client.bundle.js.map
