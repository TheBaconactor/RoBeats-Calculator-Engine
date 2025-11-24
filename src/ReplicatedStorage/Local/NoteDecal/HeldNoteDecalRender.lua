-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_6 = require(game.ReplicatedStorage.Local.HeldNoteState)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_9 = require(game.ReplicatedStorage.Local.NoteDecal.TriggerNoteEffectDecal)
local v_u_10 = require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_90 = {
    ["_new"] = function(_, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: _new ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_3, (copy 3): v_u_5, (copy 4): v_u_1, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_6, (copy 8): v_u_2, (copy 9): v_u_9, (copy 10): v_u_8 ]]
        local v_u_18 = {}
        v_u_18.rebind = function(_, p19, p20, p21, p22, p23, p24, p25, _, _) --[[ Name: rebind ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): p_u_11, (ref 2): p_u_12, (ref 3): p_u_13, (ref 4): p_u_14, (ref 5): p_u_15, (ref 6): p_u_16, (ref 7): p_u_17 ]]
            p_u_11 = p19
            p_u_12 = p20
            p_u_13 = p21
            p_u_14 = p22
            p_u_15 = p23
            p_u_16 = p24
            p_u_17 = p25
        end;
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = 0
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = true
        local v_u_35 = v_u_10:new(0.15)
        local v_u_36 = true
        local v_u_37 = 0.85
        local v_u_38 = 0.4
        v_u_18.cons = function(p39) --[[ Name: cons ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_26, (ref 3): p_u_11, (ref 4): v_u_27, (ref 5): p_u_13, (ref 6): v_u_28, (ref 7): v_u_34, (ref 8): v_u_3, (ref 9): v_u_5, (ref 10): v_u_37, (ref 11): v_u_38, (ref 12): v_u_29, (ref 13): p_u_12, (ref 14): v_u_1, (ref 15): p_u_16, (ref 16): v_u_30, (ref 17): v_u_32, (ref 18): v_u_33, (ref 19): v_u_31, (ref 20): v_u_4 ]]
            v_u_36 = true
            v_u_26 = p_u_11._ui_manager:get_decal_ui_manager()
            v_u_27 = p_u_11:es_gamelocal_get_tracksystems():get(p_u_13)
            v_u_28 = 0
            v_u_34 = p_u_11._player_settings_manager:get_key(v_u_3.Key.HeldNoteTransparent) == true
            local _, v40 = v_u_27:get_player_note_display_mode_and_decal_id()
            local v41 = v_u_5:singleton():get_info_for_id(v40)
            v_u_37 = v41:get_note_size_scale()
            v_u_38 = v41:get_held_note_body_size_scale()
            v_u_29 = p_u_11._object_pool:depool_key_instance_type("HeldNoteDecalRender", "ImageLabel")
            v_u_29.Visible = true
            v_u_29.Image = v41:get_held_note_fill_assetid(p_u_12)
            v_u_29.ImageTransparency = v_u_1:tra(1)
            v_u_29.BackgroundTransparency = v_u_1:tra(0)
            v_u_29.Name = v_u_1:gen_name(string.format("HeldNoteHead slot(%d) track(%d) index(%d)", p_u_13, p_u_12, p_u_16))
            v_u_29.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_29.Parent = v_u_26:get_screengui()
            v_u_30 = p_u_11._object_pool:depool_key_instance_type("HeldNoteDecalRender", "ImageLabel")
            v_u_30.Visible = true
            v_u_30.Image = v41:get_held_note_outline_assetid(p_u_12)
            v_u_30.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_30.ImageTransparency = v_u_1:tra(1)
            v_u_30.BackgroundTransparency = v_u_1:tra(0)
            v_u_30.Position = UDim2.new(0, 0, 0, 0)
            v_u_30.Size = UDim2.new(1, 0, 1, 0)
            v_u_30.Name = v_u_1:gen_name("Outline")
            v_u_30.AnchorPoint = Vector2.new(0, 0)
            v_u_30.Parent = v_u_29
            v_u_32 = p_u_11._object_pool:depool_key_instance_type("HeldNoteDecalRender", "ImageLabel")
            v_u_32.Visible = true
            v_u_32.Image = v41:get_held_note_fill_assetid(p_u_12)
            v_u_32.ImageTransparency = v_u_1:tra(1)
            v_u_32.BackgroundTransparency = v_u_1:tra(0)
            v_u_32.Name = v_u_1:gen_name(string.format("HeldNoteTail slot(%d) track(%d) index(%d)", p_u_13, p_u_12, p_u_16))
            v_u_32.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_32.Parent = v_u_26:get_screengui()
            v_u_33 = p_u_11._object_pool:depool_key_instance_type("HeldNoteDecalRender", "ImageLabel")
            v_u_33.Visible = true
            v_u_33.Image = v41:get_held_note_outline_assetid(p_u_12)
            v_u_33.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_33.ImageTransparency = v_u_1:tra(1)
            v_u_33.BackgroundTransparency = v_u_1:tra(0)
            v_u_33.Position = UDim2.new(0, 0, 0, 0)
            v_u_33.Size = UDim2.new(1, 0, 1, 0)
            v_u_33.Name = v_u_1:gen_name("Outline")
            v_u_33.AnchorPoint = Vector2.new(0, 0)
            v_u_33.Parent = v_u_32
            v_u_31 = p_u_11._object_pool:depool_key_instance_type("HeldNoteDecalRender_Slice", "ImageLabel")
            v_u_31.Visible = true
            v_u_31.ScaleType = Enum.ScaleType.Slice
            v_u_31.SliceCenter = Rect.new(81, 89, 81, 302)
            v_u_31.Image = v41:get_held_note_body_assetid()
            v_u_31.ImageTransparency = v_u_1:tra(1)
            v_u_31.BackgroundTransparency = v_u_1:tra(0)
            v_u_31.Name = v_u_1:gen_name(string.format("HeldNoteBody slot(%d) track(%d) index(%d)", p_u_13, p_u_12, p_u_16))
            v_u_31.AnchorPoint = Vector2.new(0.5, 1)
            v_u_31.Parent = v_u_26:get_screengui()
            if v_u_27:get_active_note_display_mode() == v_u_4.DecalDown then
                v_u_29.ZIndex = 8
                v_u_30.ZIndex = 9
                v_u_32.ZIndex = 5
                v_u_33.ZIndex = 6
                v_u_31.ZIndex = 7
            else
                v_u_29.ZIndex = 5
                v_u_30.ZIndex = 6
                v_u_32.ZIndex = 8
                v_u_33.ZIndex = 9
                v_u_31.ZIndex = 7
            end;
            p39:update_visual(0)
        end;
        local function _() --[[ Name: get_head_position ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): p_u_12, (ref 4): p_u_17 ]]
            local v42, v43 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
            return v42:Lerp(v43, (p_u_17:get_head_t()));
        end;
        local function _() --[[ Name: get_tail_position ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): p_u_12, (ref 4): p_u_17 ]]
            local v44, v45 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
            return v44:Lerp(v45, (p_u_17:get_tail_t()));
        end;
        v_u_18.update_visual = function(_, p46) --[[ Name: update_visual ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): p_u_11, (ref 3): p_u_13, (ref 4): p_u_17, (ref 5): v_u_31, (ref 6): v_u_29, (ref 7): v_u_32, (ref 8): v_u_26, (ref 9): v_u_37, (ref 10): v_u_27, (ref 11): p_u_12, (ref 12): v_u_28, (ref 13): p_u_15, (ref 14): v_u_34, (ref 15): v_u_6, (ref 16): v_u_30, (ref 17): v_u_33, (ref 18): v_u_38, (ref 19): v_u_2 ]]
            local v47 = p_u_17:color3_for_slot(p_u_13, (v_u_7:get_server_game_instance_player_powerbar_active(p_u_11._players._slots:get(p_u_13))))
            v_u_31.ImageColor3 = v47
            v_u_29.ImageColor3 = v47
            v_u_32.ImageColor3 = v47
            local v48, _ = v_u_26:get_track_size_and_position()
            local v49 = v48._x * v_u_37
            v_u_29.Size = UDim2.new(0, v49, 0, v49)
            v_u_32.Size = v_u_29.Size
            local _, v50 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
            local v51, v52 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
            local v53 = v51:Lerp(v52, (p_u_17:get_head_t()))
            local v54, v55 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
            local v56 = v54:Lerp(v55, (p_u_17:get_tail_t()))
            if p_u_17:did_trigger_head() then
                if p_u_15 >= v_u_28 then
                    v50 = v53
                end;
            else
                v50 = v53
            end;
            v_u_29.Position = UDim2.new(0, v50.X, 0, v50.Y)
            v_u_32.Position = UDim2.new(0, v56.X, 0, v56.Y)
            local v57, v58, v59, v60, v61
            if v_u_34 then
                v57 = 0
                v58 = 1
                v59 = 0.25
                v60 = 0.25
                v61 = 0.5
            else
                v57 = 0
                v58 = 1
                v59 = 0
                v60 = 0
                v61 = 0
            end;
            local v62 = p_u_17:get_state()
            if v62 == v_u_6.Pre then
                v_u_29.ImageTransparency = v57
                v_u_30.ImageTransparency = v57
            else
                v_u_29.ImageTransparency = v58
                v_u_30.ImageTransparency = v58
            end;
            if v62 == v_u_6.Passed and p_u_17:did_trigger_tail() then
                v_u_32.ImageTransparency = v58
                v_u_33.ImageTransparency = v58
            elseif p_u_17:tail_visible() then
                v_u_32.ImageTransparency = v59
                v_u_33.ImageTransparency = v60
            else
                v_u_32.ImageTransparency = v58
                v_u_33.ImageTransparency = v58
            end;
            v_u_31.Position = UDim2.new(0, v50.X, 0, v50.Y)
            v_u_31.Size = UDim2.new(0, v48._x * v_u_38, 0, -(v56.Y - v50.Y))
            local v63 = false
            if v62 == v_u_6.HoldMissedActive then
                v61 = 0.9
            elseif v62 == v_u_6.Passed and p_u_17:did_trigger_tail() then
                v63 = true
                v61 = 1
            end;
            if v63 then
                v_u_31.ImageTransparency = v61
            else
                v_u_31.ImageTransparency = v_u_2:Expt(v_u_31.ImageTransparency, v61, v_u_2:NormalizedDefaultExptValueInSeconds(0.15), p46)
            end;
        end;
        local function _() --[[ Name: is_local_slot ]] --[[ Line: 250 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_11 ]]
            return p_u_13 == p_u_11:get_local_game_slot();
        end;
        local function f_update_holding_flash(p64) --[[ Name: update_holding_flash ]] --[[ Line: 254 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): p_u_17, (ref 3): v_u_6, (copy 4): v_u_35, (ref 5): p_u_13, (ref 6): p_u_11, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): p_u_12, (ref 10): v_u_7, (ref 11): v_u_9 ]]
            if v_u_18:get_visible() == true then
                if p_u_17:get_state() == v_u_6.Holding then
                    v_u_35:update(p64)
                    if v_u_35:do_flash() and p_u_13 == p_u_11:get_local_game_slot() then
                        local _, v65 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
                        p_u_11._effects:add_effect(v_u_9:new(p_u_11, p_u_13, v65, v_u_9.NOTE_RESULT_SPECIAL_FADE):set_image_color((p_u_17:color3_for_slot(p_u_13, (v_u_7:get_server_game_instance_player_powerbar_active(p_u_11._players._slots:get(p_u_13)))))))
                    end;
                end;
            end;
        end;
        v_u_18.update = function(_, p66) --[[ Name: update ]] --[[ Line: 275 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): p_u_11, (copy 3): f_update_holding_flash ]]
            v_u_28 = p_u_11:es_gamelocal_get_audiomanager():get_current_time_ms()
            f_update_holding_flash(p66)
        end;
        v_u_18.cleanup = function(p67) --[[ Name: cleanup ]] --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): p_u_11 ]]
            v_u_29.Parent = nil
            v_u_30.Parent = nil
            v_u_31.Parent = nil
            v_u_32.Parent = nil
            v_u_33.Parent = nil
            p_u_11._object_pool:repool("HeldNoteDecalRender", v_u_29)
            p_u_11._object_pool:repool("HeldNoteDecalRender", v_u_30)
            p_u_11._object_pool:repool("HeldNoteDecalRender", v_u_32)
            p_u_11._object_pool:repool("HeldNoteDecalRender", v_u_33)
            p_u_11._object_pool:repool("HeldNoteDecalRender_Slice", v_u_31)
            v_u_29 = nil
            v_u_30 = nil
            v_u_31 = nil
            v_u_32 = nil
            v_u_33 = nil
            p_u_11._lua_pool:repool("HeldNoteDecalRender", p67)
        end;
        v_u_18.note_on_hit = function(p68, p69) --[[ Name: note_on_hit ]] --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_6, (ref 3): v_u_8, (ref 4): p_u_11, (ref 5): v_u_9, (ref 6): p_u_13, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): p_u_12 ]]
            if p68:get_visible() == true then
                local v70 = p_u_17:get_state()
                if v70 == v_u_6.Pre then
                    if p69 ~= v_u_8.NoteResult_Miss then
                        local l__effects_0 = p_u_11._effects
                        local v71 = v_u_9
                        local v72 = p_u_11
                        local v73 = p_u_13
                        local v74, v75 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
                        l__effects_0:add_effect(v71:new(v72, v73, v74:Lerp(v75, (p_u_17:get_head_t())), p69))
                        return;
                    end;
                elseif v70 == v_u_6.HoldMissedActive and p69 ~= v_u_8.NoteResult_Miss then
                    local l__effects_1 = p_u_11._effects
                    local v76 = v_u_9
                    local v77 = p_u_11
                    local v78 = p_u_13
                    local v79, v80 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
                    l__effects_1:add_effect(v76:new(v77, v78, v79:Lerp(v80, (p_u_17:get_tail_t())), p69))
                end;
            end;
        end;
        v_u_18.note_on_release = function(p81, p82) --[[ Name: note_on_release ]] --[[ Line: 325 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_6, (ref 3): v_u_8, (ref 4): p_u_11, (ref 5): v_u_9, (ref 6): p_u_13, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): p_u_12 ]]
            if p81:get_visible() == true then
                local v83 = p_u_17:get_state()
                if v83 == v_u_6.Holding or v83 == v_u_6.HoldMissedActive then
                    if p82 == v_u_8.NoteResult_Miss then
                        return;
                    end;
                    if p82 ~= v_u_8.NoteResult_Miss then
                        local l__effects_2 = p_u_11._effects
                        local v84 = v_u_9
                        local v85 = p_u_11
                        local v86 = p_u_13
                        local v87, v88 = v_u_26:get_start_end_point_for_track_system_index(v_u_27, p_u_12)
                        l__effects_2:add_effect(v84:new(v85, v86, v87:Lerp(v88, (p_u_17:get_tail_t())), p82))
                    end;
                end;
            end;
        end;
        v_u_18.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 343 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        v_u_18.set_visible = function(_, p89) --[[ Name: set_visible ]] --[[ Line: 345 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_29, (ref 3): v_u_30, (ref 4): v_u_31, (ref 5): v_u_32, (ref 6): v_u_33 ]]
            v_u_36 = p89
            v_u_29.Visible = p89
            v_u_30.Visible = p89
            v_u_31.Visible = p89
            v_u_32.Visible = p89
            v_u_33.Visible = p89
        end;
        return v_u_18;
    end
}
v_u_90.new = function(_, p91, p92, p93, p94, p95, p96, p97, p98, p99) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_90 ]]
    local v100 = p91._lua_pool:depool("HeldNoteDecalRender")
    if v100 == nil then
        local v101 = v_u_90:_new(p91, p92, p93, p94, p95, p96, p97, p98, p99)
        v101:cons()
        return v101;
    else
        v100:rebind(p91, p92, p93, p94, p95, p96, p97, p98, p99)
        v100:cons()
        return v100;
    end;
end;
v_u_90.prepool = function(_, p102) --[[ Name: prepool ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_90 ]]
    p102._lua_pool:repool("HeldNoteDecalRender", v_u_90:_new())
end;
return v_u_90;
