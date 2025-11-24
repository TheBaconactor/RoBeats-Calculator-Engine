-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p11) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_1, (copy 5): v_u_2 ]]
        local v_u_12 = p11 == nil and {} or p11
        local v_u_15 = {
            ["filter_text"] = function(_, p13) --[[ Name: filter_text ]] --[[ Line: 228 ]]
                if #p13 > 255 then
                    return true, string.sub(p13, 1, 255);
                else
                    local v14 = string.lower(p13)
                    if v14[1] == "f" and (v14[2] == "u" and (v14[3] == "c" and v14[4] == "k")) or (v14[1] == "s" and (v14[2] == "h" and (v14[3] == "i" and v14[4] == "t")) or v14[1] == "c" and (v14[2] == "u" and (v14[3] == "n" and v14[4] == "t"))) then
                        return true, string.rep("#", #p13);
                    else
                        return false, p13;
                    end;
                end;
            end
        }
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = ""
        local l_TextColor3_0 = p_u_7.TextColor3
        local v_u_19 = Color3.new(p_u_7.TextColor3.r * 0.65, p_u_7.TextColor3.g * 0.65, p_u_7.TextColor3.b * 0.65)
        local v_u_20 = false
        local v_u_21 = 0
        local v_u_22 = ""
        local v_u_23 = false
        local v_u_24 = v_u_3:new()
        local v_u_25 = true
        local v_u_26 = -1
        local v_u_27 = false
        local v_u_28 = true
        local v_u_29 = false
        local v_u_30 = nil
        local v_u_31 = ""
        v_u_15.set_empty_message = function(p32, p33) --[[ Name: set_empty_message ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            v_u_31 = p33
            return p32;
        end;
        local function f_tonumber_with_limits(p34) --[[ Name: tonumber_with_limits ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v35 = tonumber(p34)
            if typeof(v35) == "number" then
                v35 = v_u_4:is_finite(v35) ~= true and 0 or v35
                if v_u_4:input_max_number() < v35 then
                    v35 = v_u_4:input_max_number()
                end;
                if v35 < -v_u_4:input_max_number() then
                    v35 = -v_u_4:input_max_number()
                end;
            end;
            return v35;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_16, (ref 3): v_u_17, (copy 4): v_u_15, (ref 5): v_u_12, (copy 6): f_tonumber_with_limits, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): v_u_28, (ref 10): v_u_30, (ref 11): v_u_29, (copy 12): v_u_24, (ref 13): v_u_5, (ref 14): v_u_25, (ref 15): v_u_18, (copy 16): p_u_7 ]]
            if p_u_8 ~= nil then
                p_u_8.CanvasSize = UDim2.new(10, 0, 10, 0)
            end;
            v_u_16 = Instance.new("ScreenGui", game.Players.LocalPlayer.PlayerGui)
            v_u_16.Enabled = false
            v_u_16.Name = "SPUITextInput"
            v_u_17 = Instance.new("TextBox", v_u_16)
            v_u_17.ClearTextOnFocus = false
            v_u_17.Text = ""
            v_u_15:set_current_text("")
            local function f_text_on_changed() --[[ Name: text_on_changed ]] --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_15, (ref 3): v_u_12, (ref 4): f_tonumber_with_limits, (ref 5): v_u_26, (ref 6): v_u_27, (ref 7): v_u_28, (ref 8): v_u_30, (ref 9): v_u_29 ]]
                if v_u_17 == nil then
                    return;
                end;
                local v36, v37 = v_u_15:filter_text(v_u_17.Text)
                v_u_15:set_current_text(v37)
                if v36 then
                    v_u_17.Text = v37
                    v_u_17:CaptureFocus()
                end;
                local v38 = v_u_12.AllowDecimals == true and (#v37 > 0 and v37:sub(#v37, #v37) == ".")
                local v39 = f_tonumber_with_limits(v37)
                local v40 = v37 == "" or v37 == "-"
                local v41
                if v_u_26 >= 0 then
                    v41 = v_u_26 < #v37
                else
                    v41 = false
                end;
                local v42
                if v_u_27 == true and (#v37 > 0 and v39 == nil) then
                    v42 = v40 == false
                else
                    v42 = false
                end;
                if v41 then
                    local v43 = string.sub(v37, 1, v_u_26)
                    v_u_15:set_current_text(v43)
                    v_u_17.Text = v43
                    v_u_17:CaptureFocus()
                    return;
                end;
                if not v42 then
                    if v_u_27 == true and v40 ~= true then
                        if v_u_28 == true then
                            local v44
                            if v_u_12.AllowDecimals == true then
                                v44 = tostring(v39)
                                if v38 == true then
                                    v44 = v44 .. "."
                                end;
                            else
                                v44 = tostring((math.floor(v39)))
                            end;
                            if v44 ~= v37 then
                                v_u_15:set_current_text(v44)
                                v_u_17.Text = v44
                                v_u_17:CaptureFocus()
                                return;
                            end;
                        end;
                        if v39 ~= nil then
                            local v45
                            if v_u_30 then
                                v45 = v_u_30(v39)
                            else
                                v45 = v39
                            end;
                            if v45 ~= v39 then
                                local v46 = tostring(v45)
                                v_u_15:set_current_text(v46)
                                v_u_17.Text = v46
                                v_u_17:CaptureFocus()
                                return;
                            end;
                        end;
                    end;
                    v_u_29 = true
                    return;
                end;
                local v47 = string.sub(v37, 1, #v37 - 1)
                while #v47 > 0 do
                    v39 = f_tonumber_with_limits(v47)
                    if v39 ~= nil then
                        break;
                    end;
                    v47 = string.sub(v47, 1, #v47 - 1)
                end;
                local v48 = #v47 == 0 and 0 or v39
                local v49
                if v_u_12.AllowDecimals == true then
                    v49 = tostring(v48)
                    if v38 == true then
                        v49 = v49 .. "."
                    end;
                else
                    v49 = tostring((math.floor(v48)))
                end;
                v_u_15:set_current_text(v49)
                v_u_17.Text = v49
                v_u_17:CaptureFocus()
            end;
            local v_u_50 = false
            v_u_24:push_back(v_u_17.Changed:Connect(function(p51) --[[ Line: 177 ]]
                --[[ Upvalues: (ref 1): v_u_50, (copy 2): f_text_on_changed, (ref 3): v_u_5 ]]
                if p51 == "Text" then
                    if v_u_50 then
                        return;
                    end;
                    v_u_50 = true
                    local v52, v53 = pcall(function() --[[ Line: 181 ]]
                        --[[ Upvalues: (ref 1): f_text_on_changed ]]
                        f_text_on_changed()
                    end)
                    if v52 == false then
                        v_u_5:warnf("textbox text_on_changed error: %s", v53)
                    end;
                    v_u_50 = false
                end;
            end))
            v_u_24:push_back(v_u_17.FocusLost:Connect(function(p54) --[[ Line: 191 ]]
                --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_15, (ref 3): v_u_18, (ref 4): v_u_17, (ref 5): p_u_8 ]]
                if p54 == true and v_u_25 == true then
                    v_u_15:raise_text_sent(v_u_18)
                    v_u_15:set_current_text("")
                    v_u_17.Text = ""
                    if p_u_8 ~= nil then
                        p_u_8.CanvasPosition = Vector2.new(0, 0)
                    end;
                end;
            end))
            spawn(function() --[[ Line: 204 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): p_u_7, (ref 3): v_u_15 ]]
                while v_u_16 ~= nil do
                    if p_u_7.Parent == nil then
                        v_u_15:cleanup()
                        return;
                    end;
                    wait(0.25)
                end;
            end)
        end;
        v_u_15.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 216 ]]
            --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_16, (ref 3): v_u_17 ]]
            for v55 = 1, v_u_24:count() do
                v_u_24:get(v55):Disconnect()
            end;
            v_u_24:clear()
            if v_u_16 ~= nil then
                v_u_16:Destroy()
                v_u_17 = nil
                v_u_16 = nil
            end;
        end;
        v_u_15.raise_text_sent = function(_, p56) --[[ Name: raise_text_sent ]] --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23 ]]
            v_u_22 = p56
            v_u_23 = true
        end;
        v_u_15.get_raise_text_sent = function(_) --[[ Name: get_raise_text_sent ]] --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_22 ]]
            local v57 = v_u_23
            v_u_23 = false
            return v57, v_u_22;
        end;
        v_u_15.is_focused = function(_) --[[ Name: is_focused ]] --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            if v_u_17 == nil then
                return false;
            else
                return v_u_17:IsFocused();
            end;
        end;
        v_u_15.set_current_text = function(p58, p59) --[[ Name: set_current_text ]] --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18 = p59
            p58:update_display()
        end;
        v_u_15.set_text = function(p60, p61) --[[ Name: set_text ]] --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            if v_u_17 then
                v_u_17.Text = p61
                p60:set_current_text(p61)
            end;
        end;
        v_u_15.get_current_text = function(_) --[[ Name: get_current_text ]] --[[ Line: 271 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v_u_15.update_display = function(p_u_62) --[[ Name: update_display ]] --[[ Line: 273 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_18, (copy 3): p_u_7, (ref 4): v_u_31, (copy 5): v_u_19, (copy 6): l_TextColor3_0, (ref 7): v_u_20, (copy 8): p_u_8 ]]
            v_u_4:ptry(function() --[[ Line: 274 ]]
                --[[ Upvalues: (copy 1): p_u_62, (ref 2): v_u_18, (ref 3): p_u_7, (ref 4): v_u_31, (ref 5): v_u_19, (ref 6): l_TextColor3_0, (ref 7): v_u_20, (ref 8): p_u_8 ]]
                if p_u_62:is_focused() == false then
                    if #v_u_18 == 0 then
                        p_u_7.Text = v_u_31
                        p_u_7.TextColor3 = v_u_19
                    else
                        p_u_7.Text = v_u_18
                        p_u_7.TextColor3 = l_TextColor3_0
                    end;
                else
                    local v63 = v_u_18
                    if v_u_20 == true then
                        v63 = v63 .. "|"
                    end;
                    p_u_7.Text = v63
                    p_u_7.TextColor3 = l_TextColor3_0
                    local v64 = p_u_7.TextBounds.X - p_u_7.Size.X.Offset
                    local v65 = v64 < 0 and 0 or v64
                    if p_u_8 ~= nil then
                        p_u_8.CanvasPosition = Vector2.new(v65, 0)
                    end;
                    return;
                end;
            end)
        end;
        v_u_15.do_focus = function(_) --[[ Name: do_focus ]] --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            if v_u_17 then
                v_u_17:CaptureFocus()
            end;
        end;
        v_u_15.do_unfocus = function(_) --[[ Name: do_unfocus ]] --[[ Line: 312 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            if v_u_17 then
                v_u_17:ReleaseFocus(false)
            end;
        end;
        v_u_15.update = function(p66, p67) --[[ Name: update ]] --[[ Line: 318 ]]
            --[[ Upvalues: (copy 1): p_u_10, (copy 2): p_u_6, (ref 3): v_u_1, (copy 4): p_u_9, (copy 5): p_u_7, (ref 6): v_u_21, (ref 7): v_u_2, (ref 8): v_u_20 ]]
            if p_u_6._input:control_just_pressed(v_u_1.KEY_CLICK) and p_u_9:uichild_get_nbounds(p_u_10, p_u_7):contains_vec2((p_u_10:get_cursor_nxy())) then
                p66:do_focus()
            end;
            if p_u_6._input:control_just_pressed(v_u_1.KEY_MENU_SPUITEXTINPUT_ESC) then
                p66:do_unfocus()
            end;
            v_u_21 = v_u_21 + v_u_2:sec_to_tick(0.35) * p67
            if v_u_21 > 1 then
                v_u_21 = 0
                v_u_20 = not v_u_20
            end;
            p66:update_display()
        end;
        v_u_15.set_send_behaviour_enabled = function(p68, p69) --[[ Name: set_send_behaviour_enabled ]] --[[ Line: 336 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            v_u_25 = p69
            return p68;
        end;
        v_u_15.set_max_length = function(p70, p71) --[[ Name: set_max_length ]] --[[ Line: 341 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p71
            return p70;
        end;
        v_u_15.get_enforce_numeric = function(_) --[[ Name: get_enforce_numeric ]] --[[ Line: 346 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v_u_15.enforce_numeric = function(p72, p73, p74) --[[ Name: enforce_numeric ]] --[[ Line: 347 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_30 ]]
            v_u_27 = p73
            v_u_30 = p74
            return p72;
        end;
        v_u_15.enforce_numeric_integer = function(p75, p76) --[[ Name: enforce_numeric_integer ]] --[[ Line: 352 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = p76
            return p75;
        end;
        v_u_15.raise_changed = function(_) --[[ Name: raise_changed ]] --[[ Line: 357 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            local v77 = v_u_29
            v_u_29 = false
            return v77;
        end;
        f_cons()
        return v_u_15;
    end
};
