-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_7 = require(game.ReplicatedStorage.Local.AudioManager)
return {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_2 ]]
        local v_u_10 = v_u_3:SPUIObjectBase()
        local l__spui_0 = p_u_8._spui
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local function _(p20) --[[ Name: set_visible ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_14, (ref 3): v_u_15 ]]
            if v_u_19 ~= p20 then
                v_u_19 = p20
                for _, v21 in v_u_14:key_itr() do
                    v21.Visible = p20
                end;
                for _, v22 in v_u_15:key_itr() do
                    v22.Visible = p20
                end;
            end;
        end;
        local function f_get_chatbar_size_nxy() --[[ Name: get_chatbar_size_nxy ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_1 ]]
            local v_u_23 = 105
            pcall(function() --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_23 ]]
                local v24 = p_u_8._chat:get_chat_window_adapter():get_chat_window():get_top_bar()
                v_u_23 = v24:get_frame_absolute_position().X + v24:get_frame_absolute_size().X
            end)
            return v_u_23 / v_u_1:screen_size().X, v_u_1:get_default_top_bar_size() / v_u_1:screen_size().Y;
        end;
        local v_u_25 = ""
        local v_u_26 = ""
        local v_u_27 = ""
        local function _(p28) --[[ Name: set_sub_text ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_17 ]]
            if v_u_27 ~= p28 then
                v_u_27 = p28
                v_u_17.Text = p28
            end;
        end;
        local v_u_29 = {
            ["TextColor3"] = v_u_1:color3(229, 255, 254),
            ["TextStrokeColor3"] = v_u_1:color3(0, 33, 255)
        }
        local v_u_30 = {
            ["TextColor3"] = v_u_1:color3(253, 255, 105),
            ["TextStrokeColor3"] = v_u_1:color3(160, 65, 6)
        }
        local v_u_31 = nil
        local v_u_32 = nil
        local function _(p33, p34) --[[ Name: set_sub_text_colors ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_17, (ref 4): v_u_1 ]]
            if v_u_31 ~= p33 or v_u_32 ~= p34 then
                v_u_17.TextColor3 = p33.TextColor3
                v_u_17.TextStrokeColor3 = p33.TextStrokeColor3
                v_u_31 = p33
                v_u_17.TextTransparency = v_u_1:tra(p34)
                v_u_32 = p34
            end;
        end;
        local v_u_35 = -1
        local function f_set_fill_pct(p_u_36) --[[ Name: set_fill_pct ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_18 ]]
            if p_u_36 ~= v_u_35 then
                v_u_35 = p_u_36
                if p_u_36 <= 0 then
                    v_u_18.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 1) })
                    return;
                end;
                if p_u_36 >= 1 then
                    v_u_18.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(1, 0) })
                    return;
                end;
                pcall(function() --[[ Line: 94 ]]
                    --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_36 ]]
                    v_u_18.Transparency = NumberSequence.new({
                        NumberSequenceKeypoint.new(0, 0),
                        NumberSequenceKeypoint.new(p_u_36, 0),
                        NumberSequenceKeypoint.new(math.min(p_u_36 + 0.01, 0.999), 1),
                        NumberSequenceKeypoint.new(1, 1)
                    })
                end)
            end;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_14, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_13, (ref 7): v_u_4, (ref 8): v_u_16, (ref 9): v_u_17, (ref 10): v_u_18, (copy 11): p_u_8, (ref 12): v_u_25, (ref 13): v_u_26, (copy 14): f_set_fill_pct, (ref 15): v_u_19, (copy 16): v_u_10 ]]
            v_u_11 = game.ReplicatedStorage.WorldUIProto.QuitDisplayV2:Clone()
            v_u_12 = v_u_11.PrimaryPart
            v_u_14 = v_u_1:get_list_of_children_of_classname(v_u_11, "ImageLabel")
            v_u_15 = v_u_1:get_list_of_children_of_classname(v_u_11, "TextLabel")
            v_u_13 = v_u_12.Size
            v_u_11.Parent = v_u_4:get_world_ui_folder()
            local l_Frame_0 = v_u_11.PrimaryPart.SurfaceGui.Frame
            v_u_16 = l_Frame_0.ButtonText
            v_u_17 = l_Frame_0.SubText
            v_u_18 = l_Frame_0.Fill.UIGradient
            local l_FillBack_0 = l_Frame_0.FillBack
            l_FillBack_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = v_u_1:tra(l_FillBack_0.ImageTransparency)
            }, "FillBack")
            local v37 = p_u_8:is_tutorial() and "Skip" or "Exit"
            v_u_16.Text = v37
            if v_u_1:is_mobile() or p_u_8._input:is_controller_active() then
                v_u_25 = "Hold to " .. string.lower(v37) .. "."
            else
                v_u_25 = "Hold \"" .. "Backspace" .. "\" to " .. string.lower(v37) .. "."
            end;
            v_u_26 = "Hold for %d more seconds to " .. string.lower(v37) .. "."
            f_set_fill_pct(0)
            if v_u_19 ~= false then
                v_u_19 = false
                for _, v38 in v_u_14:key_itr() do
                    v38.Visible = false
                end;
                for _, v39 in v_u_15:key_itr() do
                    v39.Visible = false
                end;
            end;
            v_u_10:layout()
        end;
        local v_u_40 = false
        local v_u_41 = 1
        local v_u_42 = v_u_3:cframe_params_default()
        v_u_10.layout = function(p43) --[[ Name: layout ]] --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): f_get_chatbar_size_nxy, (copy 2): l__spui_0, (ref 3): v_u_41, (copy 4): v_u_42, (ref 5): v_u_11 ]]
            local v44, v45 = f_get_chatbar_size_nxy()
            p43:opt_rescale_to_max_nxy(l__spui_0, math.min(v44 * 3, 0.35), math.min(v45 * 1.5, 0.25), v_u_41)
            v_u_42.PositionNXY:set(v44, v45 * 0.375)
            v_u_42.OffsetXYZ:from_vector3(p43:anchored_offset(0, 0))
            local v46, v47 = p43:opt_update_cframe_params(l__spui_0, v_u_42)
            if v46 == true then
                v_u_11:SetPrimaryPartCFrame(v47)
            end;
        end;
        local v_u_48 = 0
        v_u_10.update = function(p49, p50, _) --[[ Name: update ]] --[[ Line: 166 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_19, (ref 5): v_u_14, (ref 6): v_u_15, (ref 7): v_u_48, (copy 8): l__spui_0, (ref 9): v_u_40, (ref 10): v_u_5, (ref 11): v_u_2, (ref 12): v_u_41, (copy 13): p_u_9, (copy 14): f_set_fill_pct, (ref 15): v_u_27, (ref 16): v_u_17, (ref 17): v_u_26, (copy 18): v_u_30, (ref 19): v_u_31, (ref 20): v_u_32, (ref 21): v_u_1, (ref 22): v_u_25, (copy 23): v_u_29 ]]
            if p_u_8:is_spectate() then
                return;
            elseif p_u_8:get_current_mode() == v_u_6.Game and p_u_8:es_gamelocal_get_audiomanager():get_current_mode() == v_u_7.Mode.Playing then
                if v_u_19 ~= true then
                    v_u_19 = true
                    for _, v51 in v_u_14:key_itr() do
                        v51.Visible = true
                    end;
                    for _, v52 in v_u_15:key_itr() do
                        v52.Visible = true
                    end;
                end;
                if p_u_8._input:get_has_frame_focused_element() == false and p49:get_nrect(l__spui_0):contains_vec2((l__spui_0:get_cursor_nxy())) then
                    v_u_40 = true
                else
                    v_u_40 = false
                end;
                if v_u_48 <= 0 then
                    if p_u_8._input:control_just_pressed(v_u_5.KEY_GAME_QUIT) or v_u_40 and p_u_8._input:control_just_pressed(v_u_5.KEY_CLICK) then
                        v_u_48 = v_u_48 + v_u_2:TimescaleToDeltaTime(p50)
                    else
                        v_u_48 = 0
                    end;
                elseif p_u_8._input:control_pressed(v_u_5.KEY_GAME_QUIT) or v_u_40 and p_u_8._input:control_pressed(v_u_5.KEY_CLICK) then
                    v_u_48 = v_u_48 + v_u_2:TimescaleToDeltaTime(p50)
                else
                    v_u_48 = 0
                end;
                v_u_41 = v_u_2:expt_sec(v_u_41, v_u_48 > 0 and 1.15 or (v_u_40 and 1.1 or 1), 0.25, p50)
                if v_u_48 >= 2 then
                    if p_u_9 then
                        p_u_9()
                    end;
                    f_set_fill_pct(1)
                    if v_u_27 ~= "Ending..." then
                        v_u_27 = "Ending..."
                        v_u_17.Text = "Ending..."
                    end;
                elseif v_u_48 > 0 then
                    local v53 = string.format(v_u_26, (math.ceil((math.max(1, 2 - v_u_48)))))
                    if v_u_27 ~= v53 then
                        v_u_27 = v53
                        v_u_17.Text = v53
                    end;
                    local v54 = v_u_30
                    if v_u_31 ~= v54 or v_u_32 ~= 1 then
                        v_u_17.TextColor3 = v54.TextColor3
                        v_u_17.TextStrokeColor3 = v54.TextStrokeColor3
                        v_u_31 = v54
                        v_u_17.TextTransparency = v_u_1:tra(1)
                        v_u_32 = 1
                    end;
                    f_set_fill_pct(v_u_48 / 2)
                else
                    v_u_48 = 0
                    local v55 = v_u_25
                    if v_u_27 ~= v55 then
                        v_u_27 = v55
                        v_u_17.Text = v55
                    end;
                    local v56 = v_u_29
                    if v_u_31 ~= v56 or v_u_32 ~= 0.5 then
                        v_u_17.TextColor3 = v56.TextColor3
                        v_u_17.TextStrokeColor3 = v56.TextStrokeColor3
                        v_u_31 = v56
                        v_u_17.TextTransparency = v_u_1:tra(0.5)
                        v_u_32 = 0.5
                    end;
                    f_set_fill_pct(0)
                end;
                p49:layout()
            else
                if v_u_19 ~= false then
                    v_u_19 = false
                    for _, v57 in v_u_14:key_itr() do
                        v57.Visible = false
                    end;
                    for _, v58 in v_u_15:key_itr() do
                        v58.Visible = false
                    end;
                end;
                v_u_48 = 0
            end;
        end;
        v_u_10.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 230 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11:Destroy()
            v_u_11 = nil
        end;
        v_u_10.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11.PrimaryPart.Position;
        end;
        v_u_10.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 238 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        v_u_10.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12.Size;
        end;
        v_u_10.set_size = function(_, p59) --[[ Name: set_size ]] --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12.Size = Vector3.new(p59.X, p59.Y, 0)
        end;
        f_cons()
        return v_u_10;
    end
};
