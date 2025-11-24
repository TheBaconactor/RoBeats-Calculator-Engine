-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_4 = require(game.ReplicatedStorage.Effects.HoldingNoteEffect)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_6 = require(game.ReplicatedStorage.Effects.TriggerNoteEffect)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_8 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_9 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_42 = {
    ["_new"] = function(_, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: _new ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_9, (copy 5): v_u_7, (copy 6): v_u_8, (copy 7): v_u_6, (copy 8): v_u_3, (copy 9): v_u_4 ]]
        local v17 = {}
        v17.rebind = function(_, p18, p19, p20, p21, p22, p23, p24) --[[ Name: rebind ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): p_u_11, (ref 3): p_u_12, (ref 4): p_u_13, (ref 5): p_u_14, (ref 6): p_u_15, (ref 7): p_u_16 ]]
            p_u_10 = p18
            p_u_11 = p19
            p_u_12 = p20
            p_u_13 = p21
            p_u_14 = p22
            p_u_15 = p23
            p_u_16 = p24
        end;
        local v_u_25 = Vector3.new()
        local v_u_26 = 0
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = Vector2.new(0, 0.25)
        local v_u_31 = Vector2.new(1, 0.925)
        local v_u_32 = Vector3.new()
        local v_u_33 = Vector3.new()
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = true
        v17.cons = function(_) --[[ Name: cons ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_25, (ref 3): v_u_26, (ref 4): p_u_10, (ref 5): v_u_30, (ref 6): v_u_31, (ref 7): v_u_32, (ref 8): v_u_33, (ref 9): v_u_27, (ref 10): v_u_5, (ref 11): v_u_28, (ref 12): v_u_29, (ref 13): v_u_34, (ref 14): p_u_16, (ref 15): v_u_35 ]]
            v_u_36 = true
            v_u_25 = Vector3.new(0, 0, 0)
            v_u_26 = 0
            if p_u_10:show_fullscreen_mobile_ui() then
                v_u_30 = Vector2.new(0, 1.15)
                v_u_31 = Vector2.new(1, 1.3250000000000002)
            else
                v_u_30 = Vector2.new(0, 0.25)
                v_u_31 = Vector2.new(1, 0.925)
            end;
            local l_NoteAdornProto_0 = game.ReplicatedStorage.ElementProtos.NoteAdornProto
            local l_Body_0 = l_NoteAdornProto_0.Body
            local l_OutlineTop_0 = l_NoteAdornProto_0.OutlineTop
            local l_OutlineBottom_0 = l_NoteAdornProto_0.OutlineBottom
            v_u_32 = l_NoteAdornProto_0.OutlineTop.Position - l_NoteAdornProto_0.PrimaryPart.Position
            v_u_33 = l_NoteAdornProto_0.OutlineBottom.Position - l_NoteAdornProto_0.PrimaryPart.Position
            v_u_27 = p_u_10._adorn_pool:depool(v_u_5.Type.Cylinder)
            v_u_5:cylinder_adorn_copy_properties(l_Body_0.Adorn, v_u_27)
            v_u_28 = p_u_10._adorn_pool:depool(v_u_5.Type.Cylinder)
            v_u_5:cylinder_adorn_copy_properties(l_OutlineTop_0.Adorn, v_u_28)
            v_u_29 = p_u_10._adorn_pool:depool(v_u_5.Type.Cylinder)
            v_u_5:cylinder_adorn_copy_properties(l_OutlineBottom_0.Adorn, v_u_29)
            v_u_26 = 0.25 + p_u_10:get_game_environment_center().Y
            v_u_34 = p_u_16:get_track():get_start_position()
            v_u_35 = p_u_16:get_track():get_end_position()
        end;
        v17.update_visual = function(_, _) --[[ Name: update_visual ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_1, (ref 3): v_u_25, (ref 4): v_u_34, (ref 5): v_u_35, (ref 6): v_u_26, (ref 7): v_u_2, (ref 8): v_u_30, (ref 9): v_u_31, (ref 10): v_u_27, (ref 11): v_u_5, (ref 12): v_u_29, (ref 13): v_u_33, (ref 14): v_u_28, (ref 15): v_u_32, (ref 16): v_u_9, (ref 17): p_u_12 ]]
            local v37 = p_u_16:get_head_t()
            v_u_1:profilebegin("Note:update_visual(CFrame)")
            v_u_25 = v_u_34:Lerp(v_u_35, v37)
            v_u_25 = Vector3.new(v_u_25.X, v_u_26, v_u_25.Z)
            local v38 = v_u_2:YForPointOf2PtLine(v_u_30, v_u_31, v_u_1:clamp(v37, 0, 1))
            v_u_27.CFrame = CFrame.new(v_u_25) * v_u_5:cylinder_up_cframe()
            v_u_27.Height = v38 * 1.5
            v_u_27.Radius = v38 * 1.5
            v_u_29.CFrame = CFrame.new(v_u_25 + v_u_33 * v38) * v_u_5:cylinder_up_cframe()
            v_u_29.Height = v38 * 0.5
            v_u_29.Radius = v38 * 1.6
            v_u_28.CFrame = CFrame.new(v_u_25 + v_u_32 * v38) * v_u_5:cylinder_up_cframe()
            v_u_28.Height = v38 * 0.25
            v_u_28.Radius = v38 * 1.6
            v_u_27.Color3 = p_u_16:color3_for_slot(p_u_12, (v_u_9:get_server_game_instance_player_powerbar_active(p_u_16:get_slot_player())))
            v_u_1:profileend()
        end;
        v17.cleanup = function(p39) --[[ Name: cleanup ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_29 ]]
            p_u_10._adorn_pool:repool(v_u_27)
            p_u_10._adorn_pool:repool(v_u_28)
            p_u_10._adorn_pool:repool(v_u_29)
            v_u_27 = nil
            v_u_28 = nil
            v_u_29 = nil
            p_u_10._lua_pool:repool("NoteAdornRender", p39)
        end;
        v17.note_on_hit = function(_, p40) --[[ Name: note_on_hit ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): p_u_10, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_6, (ref 6): v_u_25, (ref 7): p_u_12, (ref 8): v_u_3, (ref 9): v_u_4 ]]
            if v_u_36 == true then
                if p_u_10._player_settings_manager:get_key(v_u_7.Key.BrightnessSettings) == v_u_8.Normal then
                    p_u_10._effects:add_effect(v_u_6:new(p_u_10, v_u_25, p40, p_u_12 == p_u_10:get_local_game_slot()))
                end;
                if p40 ~= v_u_3.NoteResult_Miss then
                    p_u_10._effects:add_effect(v_u_4:new(p_u_10, v_u_25, p40))
                end;
            end;
        end;
        v17.set_visible = function(_, p41) --[[ Name: set_visible ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_29 ]]
            v_u_36 = p41
            v_u_27.Visible = p41
            v_u_28.Visible = p41
            v_u_29.Visible = p41
        end;
        return v17;
    end
}
v_u_42.new = function(_, p43, p44, p45, p46, p47, p48, p49) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_42 ]]
    local v50 = p43._lua_pool:depool("NoteAdornRender")
    if v50 == nil then
        local v51 = v_u_42:_new(p43, p44, p45, p46, p47, p48, p49)
        v51:cons()
        return v51;
    else
        v50:rebind(p43, p44, p45, p46, p47, p48, p49)
        v50:cons()
        return v50;
    end;
end;
v_u_42.prepool = function(_, p52) --[[ Name: prepool ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_42 ]]
    p52._lua_pool:repool("NoteAdornRender", v_u_42:_new())
end;
return v_u_42;
