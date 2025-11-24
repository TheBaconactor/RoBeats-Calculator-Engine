-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_6 = require(game.ReplicatedStorage.Local.NoteDecal.TriggerNoteEffectDecal)
local v_u_41 = {
    ["_new"] = function(_, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: _new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_5, (copy 6): v_u_6 ]]
        local v14 = {}
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = true
        local v_u_20 = 0.85
        v14.rebind = function(_, p21, p22, p23, p24, p25, p26, p27) --[[ Name: rebind ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): p_u_7, (ref 2): p_u_8, (ref 3): p_u_9, (ref 4): p_u_10, (ref 5): p_u_11, (ref 6): p_u_12, (ref 7): p_u_13 ]]
            p_u_7 = p21
            p_u_8 = p22
            p_u_9 = p23
            p_u_10 = p24
            p_u_11 = p25
            p_u_12 = p26
            p_u_13 = p27
        end;
        v14.cons = function(p28) --[[ Name: cons ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_15, (ref 3): p_u_7, (ref 4): v_u_16, (ref 5): p_u_9, (ref 6): v_u_3, (ref 7): v_u_20, (ref 8): v_u_17, (ref 9): p_u_8, (ref 10): v_u_1, (ref 11): p_u_12, (ref 12): v_u_18 ]]
            v_u_19 = true
            v_u_15 = p_u_7._ui_manager:get_decal_ui_manager()
            v_u_16 = p_u_7:es_gamelocal_get_tracksystems():get(p_u_9)
            local _, v29 = v_u_16:get_player_note_display_mode_and_decal_id()
            local v30 = v_u_3:singleton():get_info_for_id(v29)
            v_u_20 = v30:get_note_size_scale()
            v_u_17 = p_u_7._object_pool:depool_key_instance_type("NoteDecalRender", "ImageLabel")
            v_u_17.Visible = true
            v_u_17.Image = v30:get_single_note_fill_assetid(p_u_8)
            v_u_17.ImageTransparency = v_u_1:tra(1)
            v_u_17.BackgroundTransparency = v_u_1:tra(0)
            v_u_17.Name = v_u_1:gen_name(string.format("NoteFill slot(%d) track(%d) index(%d)", p_u_9, p_u_8, p_u_12))
            v_u_17.ZIndex = 5
            v_u_17.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_17.Parent = v_u_15:get_screengui()
            v_u_18 = p_u_7._object_pool:depool_key_instance_type("NoteDecalRender", "ImageLabel")
            v_u_18.Visible = true
            v_u_18.Image = v30:get_single_note_outline_assetid(p_u_8)
            v_u_18.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_18.ImageTransparency = v_u_1:tra(1)
            v_u_18.BackgroundTransparency = v_u_1:tra(0)
            v_u_18.Position = UDim2.new(0, 0, 0, 0)
            v_u_18.Size = UDim2.new(1, 0, 1, 0)
            v_u_18.Name = v_u_1:gen_name("Outline")
            v_u_18.ZIndex = 6
            v_u_18.AnchorPoint = Vector2.new(0, 0)
            v_u_18.Parent = v_u_17
            p28:update_visual(0)
        end;
        local function f_get_head_position() --[[ Name: get_head_position ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): p_u_8, (ref 4): p_u_13, (ref 5): v_u_2 ]]
            local v31, v32 = v_u_15:get_start_end_point_for_track_system_index(v_u_16, p_u_8)
            local v33 = p_u_13:get_head_t()
            return Vector2.new(v_u_2:Lerp(v31.X, v32.X, v33), v_u_2:Lerp(v31.Y, v32.Y, v33));
        end;
        v14.update_visual = function(_, _) --[[ Name: update_visual ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_20, (ref 3): v_u_17, (copy 4): f_get_head_position, (ref 5): v_u_4, (ref 6): p_u_13, (ref 7): p_u_9 ]]
            local v34, _ = v_u_15:get_track_size_and_position()
            local v35 = v34._x * v_u_20
            v_u_17.Size = UDim2.new(0, v35, 0, v35)
            local v36 = f_get_head_position()
            v_u_17.Position = UDim2.new(0, v36.X, 0, v36.Y)
            v_u_17.ImageColor3 = p_u_13:color3_for_slot(p_u_9, (v_u_4:get_server_game_instance_player_powerbar_active(p_u_13:get_slot_player())))
        end;
        v14.cleanup = function(p37) --[[ Name: cleanup ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): p_u_7 ]]
            v_u_17.Parent = nil
            v_u_18.Parent = nil
            p_u_7._object_pool:repool("NoteDecalRender", v_u_17)
            p_u_7._object_pool:repool("NoteDecalRender", v_u_18)
            v_u_17 = nil
            v_u_18 = nil
            p_u_7._lua_pool:repool("NoteDecalRender", p37)
        end;
        v14.note_on_hit = function(p38, p39) --[[ Name: note_on_hit ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_7, (ref 3): v_u_6, (ref 4): p_u_9, (copy 5): f_get_head_position ]]
            if p38:get_visible() == true then
                if p39 ~= v_u_5.NoteResult_Miss then
                    p_u_7._effects:add_effect(v_u_6:new(p_u_7, p_u_9, f_get_head_position(), p39))
                end;
            end;
        end;
        v14.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v14.set_visible = function(_, p40) --[[ Name: set_visible ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_17 ]]
            v_u_19 = p40
            v_u_17.Visible = p40
        end;
        return v14;
    end
}
v_u_41.new = function(_, p42, p43, p44, p45, p46, p47, p48) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_41 ]]
    local v49 = p42._lua_pool:depool("NoteDecalRender")
    if v49 == nil then
        local v50 = v_u_41:_new(p42, p43, p44, p45, p46, p47, p48)
        v50:cons()
        return v50;
    else
        v49:rebind(p42, p43, p44, p45, p46, p47, p48)
        v49:cons()
        return v49;
    end;
end;
v_u_41.prepool = function(_, p51) --[[ Name: prepool ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_41 ]]
    p51._lua_pool:repool("NoteDecalRender", v_u_41:_new())
end;
return v_u_41;
