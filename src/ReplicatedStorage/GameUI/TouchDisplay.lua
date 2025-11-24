-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.GameLocalMode)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_8 = {
    ["Pane"] = {}
}
v_u_8.Pane.new = function(_, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_6, (copy 4): v_u_2 ]]
    local v_u_11 = {}
    local v_u_12 = nil
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = -1
    local function _() --[[ Name: cons ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15, (copy 5): v_u_11 ]]
        v_u_12 = game.ReplicatedStorage.WorldUIProto.TouchSection:Clone()
        v_u_13 = v_u_12.PrimaryPart
        v_u_14 = v_u_13.CFrame
        v_u_15 = v_u_13.SurfaceGui.Frame.ImageLabel
        v_u_11:set_enabled(false)
        v_u_11:set_alpha(0.15)
    end;
    local v_u_17 = nil
    v_u_11.set_enabled = function(_, p18) --[[ Name: set_enabled ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_12, (ref 3): v_u_4 ]]
        if p18 == v_u_17 then
            return;
        else
            v_u_17 = p18
            if v_u_17 then
                v_u_12.Parent = v_u_4:get_world_ui_folder()
            else
                v_u_12.Parent = v_u_4:get_game_lighting()
            end;
        end;
    end;
    v_u_11.set_alpha = function(_, p19) --[[ Name: set_alpha ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_15, (ref 3): v_u_1 ]]
        if v_u_16 ~= p19 then
            v_u_16 = p19
            v_u_15.ImageTransparency = v_u_1:tra(v_u_16)
        end;
    end;
    local v_u_20 = 0
    local v_u_21 = 0
    v_u_11.set_pos_nxy = function(p22, p23, p24) --[[ Name: set_pos_nxy ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21 ]]
        v_u_20 = p23
        v_u_21 = p24
        return p22;
    end;
    v_u_11.update = function(p25, p26, p27) --[[ Name: update ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_6, (ref 3): v_u_2, (ref 4): v_u_16 ]]
        p25:set_alpha(p_u_9:get_current_mode() ~= v_u_6.Game and 0 or (p27 == true and 0.4 or v_u_2:expt_sec(v_u_16, 0.15, 0.25, p26)))
    end;
    v_u_11.layout = function(_, p28) --[[ Name: layout ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_1, (ref 5): v_u_14, (ref 6): v_u_13, (ref 7): v_u_12 ]]
        local v29 = p_u_10:get_cframe({
            ["PositionNXY"] = Vector2.new(v_u_20 + p28 / 2, v_u_21 + 0.5)
        })
        if v_u_1:cframe_delta(v_u_14, v29) > 0.001 then
            v_u_13.CFrame = v29
            v_u_14 = v29
            local v30 = p_u_10:get_size_from_nxy(p28, 1)
            v_u_12.PrimaryPart.Size = Vector3.new(v30.X, v30.Y)
        end;
    end;
    v_u_11.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        v_u_12.Parent = nil
    end;
    local v31 = game.ReplicatedStorage.WorldUIProto.TouchSection:Clone()
    v_u_13 = v31.PrimaryPart
    v_u_14 = v_u_13.CFrame
    v_u_15 = v_u_13.SurfaceGui.Frame.ImageLabel
    v_u_11:set_enabled(false)
    v_u_11:set_alpha(0.15)
    return v_u_11;
end;
v_u_8.new = function(_, p_u_32) --[[ Name: new ]] --[[ Line: 97 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_7, (copy 5): v_u_6, (copy 6): v_u_2, (copy 7): v_u_5 ]]
    local v_u_33 = {}
    local v_u_34 = false
    local v_u_35 = v_u_3:new()
    local l__spui_0 = p_u_32._spui
    local function f_cons() --[[ Name: cons ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_1, (copy 3): v_u_35, (ref 4): v_u_8, (copy 5): p_u_32, (copy 6): l__spui_0, (copy 7): v_u_33 ]]
        v_u_34 = v_u_1:is_mobile()
        for v36 = 1, 4 do
            v_u_35:push_back(v_u_8.Pane:new(p_u_32, l__spui_0):set_pos_nxy((v36 - 1) * 0.25, 0))
        end;
        if v_u_34 then
            for v37 = 1, v_u_35:count() do
                v_u_35:get(v37):set_enabled(true)
            end;
            v_u_33:layout()
        end;
    end;
    v_u_33.set_enabled = function(p38, p39) --[[ Name: set_enabled ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        v_u_34 = p39
        return p38;
    end;
    v_u_33.layout = function(_) --[[ Name: layout ]] --[[ Line: 126 ]]
        --[[ Upvalues: (copy 1): p_u_32, (copy 2): v_u_35 ]]
        local v40, v41, v42 = p_u_32._input:get_touch_track_ends()
        v_u_35:get(1):set_pos_nxy(0, 0)
        v_u_35:get(1):layout(v40 - 0)
        v_u_35:get(2):set_pos_nxy(v40, 0)
        v_u_35:get(2):layout(v41 - v40)
        v_u_35:get(3):set_pos_nxy(v41, 0)
        v_u_35:get(3):layout(v42 - v41)
        v_u_35:get(4):set_pos_nxy(v42, 0)
        v_u_35:get(4):layout(1 - v42)
    end;
    v_u_33.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): v_u_35 ]]
        for v43 = 1, v_u_35:count() do
            v_u_35:get(v43):teardown()
        end;
    end;
    v_u_33.update = function(p44, p45, _) --[[ Name: update ]] --[[ Line: 148 ]]
        --[[ Upvalues: (ref 1): v_u_34, (copy 2): v_u_35, (copy 3): p_u_32, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_1, (ref 7): v_u_2, (ref 8): v_u_5 ]]
        if v_u_34 then
            for v46 = 1, v_u_35:count() do
                v_u_35:get(v46):set_enabled(true)
            end;
            local v47 = p_u_32:es_gamelocal_get_tracksystems():get(p_u_32:get_local_game_slot())
            local v48
            if v47 then
                v48 = v47:get_active_note_display_mode() == v_u_7.DecalDown and true or v47:get_active_note_display_mode() == v_u_7.DecalUp
            else
                v48 = false
            end;
            if p_u_32:show_fullscreen_mobile_ui() and (v48 ~= true and (p_u_32:get_current_mode() == v_u_6.Game and p_u_32._camera_manager:camera_transitioning() ~= true)) then
                local v49 = v_u_1:get_camera():WorldToScreenPoint(p_u_32:es_gamelocal_get_local_tracksystem():es_get_track(1):get_end_position()).X / v_u_1:screen_size().X
                local v50 = v_u_1:get_camera():WorldToScreenPoint(p_u_32:es_gamelocal_get_local_tracksystem():es_get_track(2):get_end_position()).X / v_u_1:screen_size().X
                local v51 = v_u_1:get_camera():WorldToScreenPoint(p_u_32:es_gamelocal_get_local_tracksystem():es_get_track(3):get_end_position()).X / v_u_1:screen_size().X
                p_u_32._input:set_touch_track_ends(v_u_2:Lerp(v49, v50, 0.5), v_u_2:Lerp(v50, v51, 0.5), v_u_2:Lerp(v51, v_u_1:get_camera():WorldToScreenPoint(p_u_32:es_gamelocal_get_local_tracksystem():es_get_track(4):get_end_position()).X / v_u_1:screen_size().X, 0.5))
            else
                p_u_32._input:set_touch_track_ends(0.25, 0.5, 0.75)
            end;
            v_u_35:get(1):update(p45, p_u_32._input:control_pressed(v_u_5.KEYCODE_TOUCH_TRACK1))
            v_u_35:get(2):update(p45, p_u_32._input:control_pressed(v_u_5.KEYCODE_TOUCH_TRACK2))
            v_u_35:get(3):update(p45, p_u_32._input:control_pressed(v_u_5.KEYCODE_TOUCH_TRACK3))
            v_u_35:get(4):update(p45, p_u_32._input:control_pressed(v_u_5.KEYCODE_TOUCH_TRACK4))
            p44:layout()
        else
            for v52 = 1, v_u_35:count() do
                v_u_35:get(v52):set_enabled(false)
            end;
        end;
    end;
    f_cons()
    return v_u_33;
end;
return v_u_8;
