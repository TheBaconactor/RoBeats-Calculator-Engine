-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_6 = require(game.ReplicatedStorage.Lobby.NPCPopup)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerStatus)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
v8:require_client(function() --[[ Line: 14 ]]
    --[[ Upvalues: (ref 1): v_u_9 ]]
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v10 = {}
local v_u_11 = {
    ["FindingCharacter"] = 0,
    ["LoadingInfo"] = 1,
    ["Loaded"] = 2,
    ["DoRemove"] = -1,
    ["Removed"] = -2
}
v10.new = function(_, p_u_12, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_6, (copy 5): v_u_7, (ref 6): v_u_9, (copy 7): v_u_2, (copy 8): v_u_4, (copy 9): v_u_5 ]]
    local v15 = {}
    local function _(p16) --[[ Name: get_character_for_userid ]] --[[ Line: 33 ]]
        local v17 = game.Players:GetPlayerByUserId(p16)
        if v17 == nil then
            return nil;
        else
            return v17.Character;
        end;
    end;
    local l_FindingCharacter_0 = v_u_11.FindingCharacter
    v15.should_remove = function(_) --[[ Name: should_remove ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): l_FindingCharacter_0, (ref 2): v_u_11 ]]
        return l_FindingCharacter_0 == v_u_11.Removed;
    end;
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = 0
    local v_u_26 = nil
    local v_u_27 = 0
    local v_u_28 = 0
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    v15.cons = function(_) --[[ Name: cons ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): l_FindingCharacter_0, (ref 2): v_u_11 ]]
        l_FindingCharacter_0 = v_u_11.FindingCharacter
    end;
    local function f_remove_children_of_name_from(p32, p33) --[[ Name: remove_children_of_name_from ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v34 = p32:GetChildren()
        for v35 = 1, #v34 do
            local v36 = v34[v35]
            if v36 == p33 then
                v36:Destroy()
                v_u_1:puts("PlayerNametag:create_nametag_on_character remove_children_of_name_from(\"%s\")", "CharacterNametag")
            end;
        end;
    end;
    v15.create_nametag_on_character = function(_, p37) --[[ Name: create_nametag_on_character ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19, (copy 3): f_remove_children_of_name_from, (ref 4): v_u_30, (ref 5): v_u_3, (ref 6): v_u_24, (ref 7): v_u_23, (ref 8): v_u_20, (ref 9): v_u_21, (ref 10): v_u_22, (copy 11): p_u_14, (ref 12): v_u_31, (ref 13): v_u_6, (copy 14): p_u_12, (ref 15): v_u_7, (ref 16): v_u_9 ]]
        v_u_18 = game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.CharacterNametag:Clone()
        v_u_18.Name = "CharacterNametag"
        v_u_19 = v_u_18.Part
        f_remove_children_of_name_from(p37, "CharacterNametag")
        v_u_18.Parent = p37
        v_u_30 = v_u_3:first_child_of_type(p37, "Humanoid")
        if v_u_30 ~= nil then
            v_u_30.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
            v_u_30.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
        end;
        local l_Name_0 = p37.Name
        v_u_24 = v_u_18.Part.SurfaceGui
        local l_Frame_0 = v_u_18.Part.SurfaceGui.Frame
        v_u_23 = l_Frame_0
        v_u_20 = l_Frame_0.RankDisplay
        v_u_21 = l_Frame_0.NameDisplay
        v_u_22 = l_Frame_0.DescriptionDisplay
        v_u_21.Text = l_Name_0
        v_u_22.Text = "-"
        v_u_20.Visible = false
        v_u_24.Enabled = false
        if p_u_14 ~= v_u_3:get_local_userid() then
            v_u_31 = v_u_6:new(p_u_12)
            v_u_31:create_popup_on_character(game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupJoinMatch, p37)
            v_u_31:set_position_offset(Vector3.new(0, 4.5, 0))
            v_u_31:set_trigger_callback(function() --[[ Line: 108 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): p_u_14, (ref 3): v_u_7, (ref 4): v_u_9 ]]
                if p_u_12._player_status_manager:contains_status_for_id(p_u_14) and p_u_12._player_status_manager:get_status_for_id(p_u_14):get_mode() == v_u_7.Mode.JoinedMatchmaking then
                    p_u_12._menus:push_menu(v_u_9:new(p_u_12._lobby_join:get_lobby(), p_u_12._spui, p_u_12._menus, p_u_12._player_status_manager:get_status_for_id(p_u_14):get_songkey(), p_u_14))
                end;
            end)
        end;
    end;
    v15.set_remove = function(_) --[[ Name: set_remove ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): l_FindingCharacter_0, (ref 2): v_u_11 ]]
        l_FindingCharacter_0 = v_u_11.DoRemove
    end;
    local v_u_38 = false
    local v_u_39 = nil
    local v_u_40 = false
    local v_u_41 = nil
    local v_u_42 = nil
    v15.off_frame_index_check_root_part_position = function(_, _) --[[ Name: off_frame_index_check_root_part_position ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_39, (ref 3): v_u_41, (ref 4): v_u_42 ]]
        local v43 = false
        if v_u_40 and v_u_39 then
            v_u_41 = v_u_39.Position
            v43 = v_u_41 ~= v_u_42 and true or v43
            v_u_42 = v_u_41
        end;
        return v43;
    end;
    v15.nametag_update_visual = function(p44, p45) --[[ Name: nametag_update_visual ]] --[[ Line: 151 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_39, (ref 3): v_u_41, (ref 4): v_u_42, (ref 5): v_u_3, (ref 6): v_u_40, (ref 7): v_u_24, (copy 8): p_u_13, (ref 9): v_u_2, (ref 10): v_u_25, (ref 11): v_u_21, (ref 12): v_u_22, (ref 13): v_u_20, (copy 14): p_u_12, (ref 15): v_u_26, (ref 16): v_u_19, (ref 17): l_FindingCharacter_0, (ref 18): v_u_11, (ref 19): v_u_38, (ref 20): v_u_29, (ref 21): v_u_4, (ref 22): v_u_27, (ref 23): v_u_23, (ref 24): v_u_5, (ref 25): v_u_28 ]]
        if v_u_30 == nil then
            p44:set_remove()
        else
            if v_u_39 == nil then
                v_u_39 = v_u_30.RootPart
                if v_u_39 == nil then
                    p44:set_remove()
                    return;
                end;
            end;
            v_u_41 = v_u_39.Position
            v_u_42 = v_u_41
            local v46 = v_u_41 + Vector3.new(0, 3.75, 0)
            local v47 = v46 - v_u_3:get_camera_cframe().p
            local l_magnitude_0 = v47.magnitude
            local v48 = v47:Dot(v_u_3:get_camera_cframe().lookVector)
            local v49 = l_magnitude_0 <= 100 and v48 >= 0
            if v_u_40 ~= v49 then
                v_u_40 = v49
                v_u_24.Enabled = v_u_40
            end;
            local v50 = v_u_2:expt_sec(v_u_25, (l_magnitude_0 > 100 and 0 or (l_magnitude_0 < 5 and 0.25 or 1)) * p_u_13:get_nametag_alpha_multiplier(), 1, p45)
            if v_u_25 ~= v50 then
                v_u_25 = v50
                local v51 = v_u_3:tra(v_u_25)
                v_u_21.TextTransparency = v51
                v_u_21.TextStrokeTransparency = v51
                v_u_22.TextTransparency = v51
                v_u_22.TextStrokeTransparency = v51
                v_u_20.ImageTransparency = v51
            end;
            if v48 > 0 and l_magnitude_0 < 100 then
                local v52 = v_u_3:lookat_camera_cframe(v46, p_u_12._spui)
                local v53 = false
                if v_u_26 == nil then
                    v53 = true
                    v_u_26 = v52
                elseif v_u_3:cframe_delta(v_u_26, v52) > 0.001 then
                    v53 = true
                    v_u_26 = v52
                end;
                if v53 == true and v_u_19 then
                    v_u_19.CFrame = v52
                end;
            end;
            if l_FindingCharacter_0 == v_u_11.Loaded then
                if v_u_38 == false then
                    v_u_38 = true
                    v_u_20.Visible = true
                    if v_u_29 and v_u_29.HasCustomIcon == true then
                        v_u_20.Image = v_u_29.CustomIcon
                        v_u_20.ImageRectSize = Vector2.new(0, 0)
                    else
                        v_u_4:render_difficulty_image(v_u_20, v_u_27)
                        v_u_20.ImageRectSize = Vector2.new(25, 25)
                    end;
                    local v54 = v_u_23.Size.X.Offset * 0.5 - v_u_21.TextBounds.X * 0.5 - 2
                    v_u_20.Position = UDim2.new(0, v54 <= 0 and 1 or v54, 0, v_u_20.Position.Y.Offset)
                    local v55 = v_u_5:singleton():get_title_for_id(v_u_28)
                    if v55:is_visible() then
                        if v55:is_guild_title() then
                            if v_u_29 and (v_u_29.IsInGuild == true and typeof(v_u_29.GuildName) == "string") then
                                v_u_22.Text = string.format("Team \'%s\'", v_u_29.GuildName)
                            else
                                v_u_22.Text = "Not in Team"
                            end;
                        else
                            v_u_22.Text = v55:get_name()
                        end;
                        v_u_21.TextColor3 = v55:get_color()
                    else
                        v_u_22.Text = ""
                        v_u_21.TextColor3 = v_u_3:color3(255, 255, 255)
                    end;
                    v_u_22.TextColor3 = v_u_21.TextColor3
                    return;
                end;
            else
                v_u_20.Visible = false
            end;
        end;
    end;
    v15.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 257 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_24, (ref 8): v_u_30, (ref 9): l_FindingCharacter_0, (ref 10): v_u_11 ]]
        local v56 = nil
        if v_u_18 ~= nil then
            v_u_18:Destroy()
        end;
        v_u_18 = nil
        v_u_19 = nil
        v_u_20 = nil
        v_u_21 = nil
        v_u_22 = nil
        v_u_23 = nil
        v_u_24 = nil
        v_u_30 = nil
        l_FindingCharacter_0 = v_u_11.Removed
        if v56 then
            v56:do_remove()
        end;
    end;
    local v_u_57 = 0
    v15.update = function(p58, p59) --[[ Name: update ]] --[[ Line: 280 ]]
        --[[ Upvalues: (ref 1): l_FindingCharacter_0, (ref 2): v_u_11, (copy 3): p_u_14, (ref 4): v_u_57, (copy 5): p_u_13, (ref 6): v_u_27, (ref 7): v_u_28, (ref 8): v_u_29, (ref 9): v_u_31, (copy 10): p_u_12, (ref 11): v_u_7 ]]
        if l_FindingCharacter_0 == v_u_11.FindingCharacter then
            local v60 = game.Players:GetPlayerByUserId(p_u_14)
            local v61
            if v60 == nil then
                v61 = nil
            else
                v61 = v60.Character
            end;
            if v61 == nil then
                v_u_57 = v_u_57 + 1
                if v_u_57 > 100 then
                    p58:set_remove()
                end;
                return;
            end;
            p58:create_nametag_on_character(v61)
            l_FindingCharacter_0 = v_u_11.LoadingInfo
            p58:nametag_update_visual(p59)
        elseif l_FindingCharacter_0 == v_u_11.LoadingInfo then
            local v62, v63, v64, v65 = p_u_13:get_player_info(p_u_14)
            if v62 then
                v_u_27 = v63
                v_u_28 = v64
                v_u_29 = v65
                l_FindingCharacter_0 = v_u_11.Loaded
            end;
            p58:nametag_update_visual(p59)
        elseif l_FindingCharacter_0 == v_u_11.Loaded then
            p58:nametag_update_visual(p59)
        elseif l_FindingCharacter_0 == v_u_11.DoRemove then
            p58:do_remove()
        end;
        if v_u_31 ~= nil then
            v_u_31:set_enabled(p_u_12._player_status_manager:contains_status_for_id(p_u_14) and p_u_12._player_status_manager:get_status_for_id(p_u_14):get_mode() == v_u_7.Mode.JoinedMatchmaking and true or false)
            v_u_31:update(p59)
        end;
    end;
    v15.set_to_load_info = function(_) --[[ Name: set_to_load_info ]] --[[ Line: 326 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): l_FindingCharacter_0, (ref 3): v_u_11 ]]
        v_u_38 = false
        if l_FindingCharacter_0 == v_u_11.Loaded then
            l_FindingCharacter_0 = v_u_11.LoadingInfo
        end;
    end;
    v15.print_debug_state = function(_) --[[ Name: print_debug_state ]] --[[ Line: 333 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_14, (ref 3): v_u_18, (ref 4): v_u_3, (ref 5): l_FindingCharacter_0, (ref 6): v_u_11 ]]
        local v66 = v_u_1
        local v67 = "PlayerNametag _userid(%s) get_character_for_userid(%s) _nametag_obj(%s) _mode(%s)"
        local v68 = tostring(p_u_14)
        local v69 = game.Players:GetPlayerByUserId(p_u_14)
        local v70
        if v69 == nil then
            v70 = nil
        else
            v70 = v69.Character
        end;
        v66:warnf(v67, v68, tostring(v70), tostring(v_u_18), (tostring(v_u_3:enum_val_to_name(l_FindingCharacter_0, v_u_11))))
    end;
    v15:cons()
    return v15;
end;
return v10;
