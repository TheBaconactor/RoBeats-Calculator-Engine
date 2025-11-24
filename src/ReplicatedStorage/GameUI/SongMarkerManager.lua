-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.ChainCombo)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_6 = require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
local v8 = {}
local v_u_9 = Vector2.new(256, 32)
local v_u_10 = Vector2.new(32, 32)
v8.new = function(_, p_u_11) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_4, (copy 6): v_u_1, (copy 7): v_u_2, (copy 8): v_u_10, (copy 9): v_u_9 ]]
    local v12 = v_u_3:SPUIObjectBase()
    v12._obj = nil
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = 0
    local v_u_20 = 1
    local v_u_21 = 1
    local v_u_22 = v_u_5:new(255, 255, 255)
    local v_u_23 = v_u_6:new(0.5)
    v12.cons = function(p24) --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_15, (ref 6): v_u_17, (ref 7): v_u_16, (ref 8): v_u_18, (ref 9): v_u_21 ]]
        p24._obj = game.ReplicatedStorage.WorldUIProto.SongMarker:Clone()
        p24._obj.Parent = v_u_7:get_world_ui_folder()
        p24._native_size = p24._obj.PrimaryPart.Size
        p24._size = p24._native_size
        v_u_13 = p24._obj.MarkerSurface
        v_u_14 = v_u_4:new(p24, p24._obj.PrimaryPart, v_u_13)
        v_u_15 = v_u_13.SurfaceGui.Frame.TimeDisplay
        v_u_17 = p24._obj.MainSurface.SurfaceGui.Frame.BarFill
        v_u_16 = p24._obj.MainSurface.SurfaceGui.Frame.BarBack
        v_u_18 = p24._obj.MarkerSurface.SurfaceGui.Frame.Cursor
        p24:set_transparency(v_u_21)
        p24:set_pct(0)
        p24:layout()
    end;
    v12.teardown = function(p25) --[[ Name: teardown ]] --[[ Line: 62 ]]
        p25._obj.Parent = nil
    end;
    v12.tint_flash = function(_) --[[ Name: tint_flash ]] --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): v_u_22 ]]
        v_u_22:set(255, 94, 110)
    end;
    v12.update_visual = function(p26, p27, _) --[[ Name: update_visual ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_15, (ref 3): v_u_1, (ref 4): v_u_19, (ref 5): v_u_2, (ref 6): v_u_20, (copy 7): v_u_23, (copy 8): v_u_22, (ref 9): v_u_21 ]]
        local v28
        if p_u_11:es_gamelocal_get_audiomanager():is_playing() then
            local v29 = p_u_11:es_gamelocal_get_audiomanager():get_song_length_ms()
            local v30 = p_u_11:es_gamelocal_get_audiomanager():get_current_time_ms()
            p26:set_pct(v30 / v29)
            local v31 = math.max(v29 - v30, 0)
            v_u_15.Text = v_u_1:format_ms_time(v31)
            v_u_19 = v_u_2:IncrementWrap(v_u_19, v_u_2:SecondsToTick(1.2) * p27, 1)
            v28 = v_u_2:YForPointOf2PtLine(Vector2.new(-1, 0.05), Vector2.new(1, 0.45), (math.sin(v_u_19 * 2 * 3.141592653589793)))
            v_u_20 = v28
            if v31 < 15000 then
                if v31 > 10000 then
                    v_u_23:set_flash_speed(2)
                elseif v31 > 5000 then
                    v_u_23:set_flash_speed(1)
                else
                    v_u_23:set_flash_speed(0.5)
                end;
                v_u_23:update(p27)
                if v_u_23:do_flash() then
                    p26:tint_flash()
                end;
            end;
        else
            v28 = 1
        end;
        v_u_22:expt_to(255, 255, 255, 1.5, p27)
        p26:set_color((v_u_22:to_color3()))
        v_u_21 = v_u_2:Expt(v_u_21, v28, v_u_2:NormalizedDefaultExptValueInSeconds(0.5), p27)
        p26:set_transparency(v_u_21)
    end;
    local v_u_32 = nil
    v12.set_color = function(_, p33) --[[ Name: set_color ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_15 ]]
        if v_u_32 ~= p33 then
            v_u_32 = p33
            v_u_17.ImageColor3 = p33
            v_u_18.ImageColor3 = p33
            v_u_15.TextColor3 = p33
        end;
    end;
    v12.set_transparency = function(_, p34) --[[ Name: set_transparency ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_2, (ref 5): v_u_20, (ref 6): v_u_15 ]]
        v_u_16.ImageTransparency = p34
        v_u_17.ImageTransparency = p34
        v_u_18.ImageTransparency = v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0), (1 - p34) * (1 - v_u_20))
        v_u_15.TextTransparency = p34
    end;
    v12.set_pct = function(p35, p36) --[[ Name: set_pct ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_10, (ref 3): v_u_9, (ref 4): v_u_14 ]]
        v_u_17.ImageRectSize = v_u_10 * Vector2.new(1 - p36, 1)
        v_u_17.Size = UDim2.new(0, v_u_9.X * (1 - p36), 0, v_u_9.Y)
        v_u_17.Position = UDim2.new(0, v_u_9.X * p36, 0, 0)
        v_u_14:set_child_relative_xy(p35:get_native_size().X * (p36 - 0.5), v_u_14:get_child_relative_xy().Y)
    end;
    local v_u_37 = v_u_3:cframe_params_default()
    v_u_37.PositionNXY:set(0.55, 0)
    local l__spui_0 = p_u_11._spui
    v12.layout = function(p38) --[[ Name: layout ]] --[[ Line: 160 ]]
        --[[ Upvalues: (copy 1): l__spui_0, (copy 2): v_u_37, (ref 3): v_u_14 ]]
        p38:opt_rescale_to_max_nxy(l__spui_0, 0.45, 0.35)
        v_u_37.OffsetXYZ:from_vector3(p38:anchored_offset(0, 0) + Vector3.new(0, -l__spui_0:get_size_from_nxy(0, 0.015).Y))
        local v39, v40 = p38:opt_update_cframe_params(l__spui_0, v_u_37)
        if v39 == true then
            p38._obj:SetPrimaryPartCFrame(v40)
        end;
        v_u_14:layout()
    end;
    v12.get_native_size = function(p41) --[[ Name: get_native_size ]] --[[ Line: 174 ]]
        return p41._native_size;
    end;
    v12.get_size = function(p42) --[[ Name: get_size ]] --[[ Line: 177 ]]
        return p42._size;
    end;
    v12.set_size = function(p43, p44) --[[ Name: set_size ]] --[[ Line: 180 ]]
        p43._size = p44
        p43._obj.PrimaryPart.Size = Vector3.new(p44.X, p44.Y, 0)
    end;
    v12.update = function(p45, p46, _) --[[ Name: update ]] --[[ Line: 185 ]]
        --[[ Upvalues: (copy 1): p_u_11 ]]
        p45:layout()
        p45:update_visual(p46, p_u_11)
    end;
    v12:cons()
    return v12;
end;
return v8;
