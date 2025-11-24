-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.PlayerConfig)
require(game.ReplicatedStorage.LocalShared.AdornPool)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_7 = {
    ["Type"] = "TriggerNoteEffectDecal",
    ["NOTE_RESULT_SPECIAL_FADE"] = -1
}
v_u_7.new = function(_, p8, p9, p10, p11) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    local v12 = p8._lua_pool:depool(v_u_7.Type)
    if v12 == nil then
        local v13 = v_u_7:_new(p8, p9, p10, p11)
        v13:cons()
        return v13;
    else
        v12:rebind(p8, p9, p10, p11)
        v12:cons()
        return v12;
    end;
end;
v_u_7.prepool = function(_, p14) --[[ Name: prepool ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    p14._lua_pool:repool(v_u_7.Type, v_u_7:_new())
end;
v_u_7._new = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: _new ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_7 ]]
    local v19 = v_u_1:EffectBase()
    v19.rebind = function(_, p20, p21, p22, p23) --[[ Name: rebind ]] --[[ Line: 37 ]]
        --[[ Upvalues: (ref 1): p_u_15, (ref 2): p_u_16, (ref 3): p_u_17, (ref 4): p_u_18 ]]
        p_u_15 = p20
        p_u_16 = p21
        p_u_17 = p22
        p_u_18 = p23
    end;
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = 0
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    v19.cons = function(p30, _) --[[ Name: cons ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_28, (ref 3): v_u_6, (ref 4): v_u_29, (ref 5): v_u_27, (ref 6): p_u_15, (ref 7): p_u_16, (ref 8): v_u_5, (ref 9): v_u_24, (ref 10): v_u_25, (ref 11): v_u_2, (ref 12): p_u_17, (ref 13): p_u_18, (ref 14): v_u_4 ]]
        v_u_26 = 0
        v_u_28 = v_u_6:new(0.5, 0)
        v_u_29 = v_u_6:new(1, 1.5)
        v_u_27 = p_u_15._ui_manager:get_decal_ui_manager()
        local _, v31 = p_u_15:es_gamelocal_get_tracksystems():get(p_u_16):get_player_note_display_mode_and_decal_id()
        local v32 = v_u_5:singleton():get_info_for_id(v31)
        v_u_24 = p_u_15._object_pool:depool_key_instance_type("TriggerNoteEffectDecal", "ImageLabel")
        v_u_25 = v_u_24:FindFirstChild("UIScale")
        if v_u_25 == nil then
            v_u_25 = Instance.new("UIScale", v_u_24)
        end;
        v_u_24.Visible = true
        v_u_24.Image = v32:get_hit_effect_assetid()
        v_u_24.ImageTransparency = v_u_2:tra(0)
        v_u_24.BackgroundTransparency = v_u_2:tra(0)
        v_u_24.Name = v_u_2:gen_name("TriggerNoteEffectDecal")
        v_u_24.ZIndex = 5
        v_u_24.AnchorPoint = Vector2.new(0.5, 0.5)
        v_u_24.Parent = v_u_27:get_screengui()
        v_u_24.Position = UDim2.new(0, p_u_17.X, 0, p_u_17.Y)
        if p_u_18 == v_u_4.NoteResult_Okay then
            v_u_24.ImageColor3 = v_u_2:color3(243, 237, 150)
        elseif p_u_18 == v_u_4.NoteResult_Great then
            v_u_24.ImageColor3 = v_u_2:color3(100, 255, 100)
        elseif p_u_18 == v_u_4.NoteResult_Perfect then
            v_u_24.ImageColor3 = v_u_2:color3(120, 255, 255)
        else
            v_u_28 = v_u_6:new(0.25, 0)
            v_u_24.ImageColor3 = v_u_2:color3(255, 255, 255)
        end;
        p30:update_visual()
    end;
    v19.set_image_color = function(p33, p34) --[[ Name: set_image_color ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24.ImageColor3 = p34
        return p33;
    end;
    v19.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_24, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): v_u_28, (ref 6): v_u_26, (ref 7): v_u_29, (ref 8): p_u_18, (ref 9): v_u_4, (ref 10): v_u_25 ]]
        local v35, _ = v_u_27:get_track_size_and_position()
        local v36 = v35._x * 0.75
        v_u_24.Size = UDim2.new(0, v36, 0, v36)
        v_u_24.ImageTransparency = v_u_2:tra(v_u_3:YForPointOf2PtLineP1P2X(0, v_u_28:min(), 1, v_u_28:max(), v_u_26))
        local v37 = v_u_3:YForPointOf2PtLineP1P2X(0, v_u_29:min(), 1, v_u_29:max(), v_u_26)
        if p_u_18 == v_u_4.NoteResult_Okay then
            v37 = v37 * 0.25
        elseif p_u_18 == v_u_4.NoteResult_Great then
            v37 = v37 * 0.5
        elseif p_u_18 == v_u_4.NoteResult_Perfect then
            v37 = v37 * 1
        end;
        v_u_25.Scale = v37
    end;
    v19.add_to_parent = function(_, _, _) end;
    v19.update = function(p38, p39, _) --[[ Name: update ]] --[[ Line: 129 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_3 ]]
        v_u_26 = v_u_26 + v_u_3:SecondsToTick(0.25) * p39
        p38:update_visual()
    end;
    v19.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26 >= 1;
    end;
    v19.do_remove = function(p40, _) --[[ Name: do_remove ]] --[[ Line: 136 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_15, (ref 3): v_u_25, (ref 4): v_u_7 ]]
        v_u_24.Parent = nil
        p_u_15._object_pool:repool("TriggerNoteEffectDecal", v_u_24)
        v_u_24 = nil
        v_u_25 = nil
        p_u_15._lua_pool:repool(v_u_7.Type, p40)
    end;
    return v19;
end;
return v_u_7;
