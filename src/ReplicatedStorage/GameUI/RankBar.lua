-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.ChainCombo)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_5 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v9 = {}
local v_u_10 = Vector2.new(13, 363)
local v_u_11 = Vector2.new(32, 32)
v9.new = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5, (copy 3): v_u_6, (copy 4): v_u_4, (copy 5): v_u_1, (copy 6): v_u_2, (copy 7): v_u_7, (copy 8): v_u_11, (copy 9): v_u_10, (copy 10): v_u_8 ]]
    local v_u_13 = v_u_3:SPUIObjectBase()
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = 0
    local l_RankF_0 = v_u_5.Value.RankF
    local v_u_25 = 0
    local v_u_26 = 0
    local v_u_27 = 0
    local v_u_28 = 0
    local v_u_29 = 0
    local function f_cons() --[[ Name: cons ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_6, (copy 3): v_u_13, (ref 4): v_u_15, (ref 5): v_u_4, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_19, (ref 10): v_u_20, (ref 11): v_u_21, (ref 12): v_u_23, (ref 13): v_u_22 ]]
        v_u_14 = game.ReplicatedStorage.WorldUIProto.RankBar:Clone()
        v_u_14.Parent = v_u_6:get_world_ui_folder()
        v_u_13._native_size = v_u_14.PrimaryPart.Size
        v_u_13._size = v_u_13._native_size
        v_u_15 = v_u_4:new(v_u_13, v_u_14.PrimaryPart, v_u_14.MarkerSurface)
        v_u_16 = v_u_14.MainSurface.SurfaceGui.Frame.BarFill
        v_u_17 = v_u_14.MainSurface.SurfaceGui.Frame.BarBack
        v_u_18 = v_u_14.MarkerSurface.SurfaceGui.Frame.RankImage
        v_u_19 = v_u_14.MarkerSurface.SurfaceGui.Frame.AverageAccuracyText
        v_u_20 = v_u_14.MarkerSurface.SurfaceGui.Frame.AverageAccuracyDisplay
        v_u_21 = v_u_14.MarkerSurface.SurfaceGui.Frame.AccuracyBackground
        v_u_19.Visible = false
        v_u_20.Visible = false
        v_u_21.Visible = false
        v_u_23 = v_u_14.EmitterSurface.ParticleEmitter
        v_u_22 = v_u_14.EmitterSurface
        v_u_23.Enabled = false
        v_u_13:set_pct(0)
        v_u_13:set_alpha(0)
        v_u_13:layout()
    end;
    v_u_13.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14:Destroy()
        v_u_14 = nil
    end;
    v_u_13.set_alpha = function(_, p30) --[[ Name: set_alpha ]] --[[ Line: 84 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_17, (ref 3): v_u_1, (ref 4): v_u_16, (ref 5): v_u_14, (ref 6): v_u_19, (ref 7): v_u_20, (ref 8): v_u_21 ]]
        v_u_27 = p30
        v_u_17.ImageTransparency = v_u_1:tra(p30)
        v_u_16.ImageTransparency = v_u_1:tra(p30)
        v_u_14.MarkerSurface.SurfaceGui.Frame.Cursor.ImageTransparency = v_u_1:tra(p30)
        v_u_14.MarkerSurface.SurfaceGui.Frame.RankImage.ImageTransparency = v_u_1:tra(p30)
        v_u_19.TextTransparency = v_u_1:tra(p30)
        v_u_20.TextTransparency = v_u_1:tra(p30)
        v_u_21.ImageTransparency = v_u_1:tra(p30)
    end;
    v_u_13.update_visual = function(p31, p32, _) --[[ Name: update_visual ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_14, (ref 3): v_u_2, (ref 4): v_u_27, (ref 5): v_u_26, (copy 6): p_u_12, (ref 7): v_u_23, (ref 8): v_u_19, (ref 9): v_u_20, (ref 10): v_u_21, (ref 11): v_u_7, (ref 12): v_u_5, (ref 13): l_RankF_0, (ref 14): v_u_28, (ref 15): v_u_25, (ref 16): v_u_24, (ref 17): v_u_15, (ref 18): v_u_29, (ref 19): v_u_18 ]]
        v_u_22.Position = v_u_14.MarkerSurface.Position
        p31:set_alpha(v_u_2:Expt(v_u_27, v_u_26, v_u_2:exptvsec(0.5), p32))
        if p_u_12:es_gamelocal_get_audiomanager():is_playing() == false then
            v_u_26 = 0
            v_u_23.Enabled = false
        else
            v_u_26 = 1
            local v33
            if p_u_12:is_spectate() then
                v33 = p_u_12:es_gamelocal_get_scoremanager():get_spectate_replicate_accuracy()
                v_u_19.Visible = false
                v_u_20.Visible = false
                v_u_21.Visible = false
            else
                local v34, v35 = p_u_12:es_gamelocal_get_scoremanager():get_score_objs()
                local v36
                if v_u_7:get_selected_mode() == v_u_7.Casual then
                    v33 = v35:get_accuracy()
                    v36 = v35:get_average_accuracy()
                else
                    v33 = v34:get_accuracy()
                    v36 = v34:get_average_accuracy()
                end;
                v_u_20.Text = string.format("%.2f%%", v36 * 100)
                v_u_19.Visible = true
                v_u_20.Visible = true
                v_u_21.Visible = true
            end;
            local v37 = 0
            local v38 = v_u_5:accuracy_to_rank_value(v33)
            local v39 = v_u_5:rank_value_to_index(v38)
            local v40 = v_u_5:contains_index(v39 + 1)
            local v41 = v_u_5:contains_index(v39 - 1)
            if v40 == false then
                v37 = 1
            elseif v40 == true and v41 == true then
                local v42 = v_u_5:rank_value_to_accuracy(v38)
                v37 = (v33 - v42) / (v_u_5:rank_value_to_accuracy(v_u_5:index_to_rank_value(v39 + 1)) - v42)
            elseif v40 == true then
                v37 = v33 / v_u_5:rank_value_to_accuracy(v_u_5:index_to_rank_value(v39 + 1))
            end;
            local v43 = v_u_5:rank_value_to_index(l_RankF_0)
            if v43 == v39 then
                v_u_28 = v37
                v_u_25 = v_u_25 + p32
            elseif v43 < v39 then
                if v_u_25 < 250 and v37 < 0.25 or p_u_12:es_gamelocal_get_audiomanager():get_current_time_ms() < 1500 then
                    v_u_28 = 1
                    v_u_25 = v_u_25 + p32
                else
                    v_u_25 = 0
                    p31:set_pct(0)
                    v_u_28 = 0
                    l_RankF_0 = v38
                    v_u_24 = 40
                    v_u_15:set_scale(3.5)
                end;
            elseif v39 < v43 then
                if v_u_25 < 250 and v37 > 0.75 then
                    v_u_28 = 0
                    v_u_25 = v_u_25 + p32
                else
                    v_u_25 = 0
                    p31:set_pct(1)
                    v_u_28 = 1
                    l_RankF_0 = v38
                    v_u_15:set_scale(0.5)
                end;
            end;
            if v_u_24 > 0 or v40 == false then
                v_u_23.Enabled = true
                v_u_24 = v_u_24 - p32
            else
                v_u_23.Enabled = false
            end;
            v_u_15:set_scale(v_u_2:Expt(v_u_15:get_scale(), 1, v_u_2:exptvsec(1.5), p32))
            if v40 == false then
                v_u_28 = 1
                p31:set_pct(1)
            else
                p31:set_pct(v_u_2:Expt(v_u_29, v_u_28, v_u_2:exptvsec(0.5), p32))
            end;
            v_u_18.Image = v_u_5:get_rank_value_icon(l_RankF_0)
        end;
    end;
    v_u_13.set_pct = function(p44, p45) --[[ Name: set_pct ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_16, (ref 3): v_u_11, (ref 4): v_u_10, (ref 5): v_u_15 ]]
        v_u_29 = p45
        v_u_16.ImageRectSize = v_u_11 * Vector2.new(1, 1 - p45)
        v_u_16.Size = UDim2.new(0, v_u_10.X, 0, v_u_10.Y * p45)
        v_u_16.Position = UDim2.new(0, 0, 0, v_u_10.Y * (1 - p45))
        v_u_15:set_child_relative_xy(v_u_15:get_child_relative_xy().X, p44:get_native_size().Y * (p45 - 0.5))
    end;
    local l__spui_0 = p_u_12._spui
    local v_u_46 = v_u_3:cframe_params_default()
    v_u_46.PositionNXY:set(0.975, 0.4)
    v_u_13.layout = function(p47) --[[ Name: layout ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): l__spui_0, (copy 2): v_u_46, (ref 3): v_u_14, (ref 4): v_u_15 ]]
        p47:opt_rescale_to_max_nxy(l__spui_0, 0.15, 0.65)
        v_u_46.OffsetXYZ:from_vector3(p47:anchored_offset(1, 0.5))
        local v48, v49 = p47:opt_update_cframe_params(l__spui_0, v_u_46)
        if v48 == true then
            v_u_14:SetPrimaryPartCFrame(v49)
        end;
        v_u_15:layout()
    end;
    v_u_13.get_native_size = function(p50) --[[ Name: get_native_size ]] --[[ Line: 223 ]]
        return p50._native_size;
    end;
    v_u_13.get_size = function(p51) --[[ Name: get_size ]] --[[ Line: 226 ]]
        return p51._size;
    end;
    v_u_13.set_size = function(p52, p53) --[[ Name: set_size ]] --[[ Line: 229 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        p52._size = p53
        v_u_14.PrimaryPart.Size = Vector3.new(p53.X, p53.Y, 0)
    end;
    local l_GameRankBar_0 = v_u_8.Test.GameRankBar
    v_u_8:register_ui_needs_refresh_should_run_test_type(l_GameRankBar_0)
    v_u_13.update = function(p54, _, _) --[[ Name: update ]] --[[ Line: 236 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): l_GameRankBar_0, (copy 3): p_u_12 ]]
        local v55 = v_u_8:singleton()
        if v55:should_run(l_GameRankBar_0) ~= false then
            local v56 = v55:get_test_state(l_GameRankBar_0):get_dt_scale()
            p54:layout()
            p54:update_visual(v56, p_u_12)
        end;
    end;
    f_cons()
    return v_u_13;
end;
return v9;
