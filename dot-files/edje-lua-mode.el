(require 'mmm-mode)
(require 'mmm-auto)
(require 'mmm-vars)

(mmm-add-classes
 '((edje-lua
    :submode lua
    :face mmm-code-submode-face
    :front "lua_script[ ]*\{"
    :back "\}")))

;; (mmm-add-mode-ext-class 'edje-mode nil 'edje-lua)

(provide 'edje-lua-mode)
