-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.PlayerListActivity)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
local v_u_13 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_14 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
return {
    ["new"] = function(_, p_u_15, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_4, (copy 6): v_u_1, (copy 7): v_u_5, (copy 8): v_u_8, (copy 9): v_u_12, (copy 10): v_u_13, (copy 11): v_u_14, (copy 12): v_u_10, (copy 13): v_u_11, (copy 14): v_u_9 ]]
        local v20 = {}
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        v20.cons = function(_) --[[ Name: cons ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_18, (copy 3): p_u_19, (copy 4): p_u_17, (ref 5): v_u_22, (ref 6): v_u_2, (copy 7): p_u_16, (ref 8): v_u_23, (copy 9): p_u_15, (ref 10): v_u_3, (ref 11): v_u_6, (ref 12): v_u_24, (ref 13): v_u_26, (ref 14): v_u_25 ]]
            v_u_21 = p_u_18:Clone()
            v_u_21:SetPrimaryPartCFrame(p_u_19.CFrame)
            v_u_21.Parent = p_u_17
            v_u_22 = v_u_2:new(p_u_16, p_u_17.PrimaryPart, v_u_21.PrimaryPart)
            v_u_23 = p_u_16:add_cycle_element(p_u_15, 1, v_u_3:new(v_u_2:new(v_u_22, v_u_21.PrimaryPart, v_u_21.ClaimButton), p_u_15._spui, function() --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_6, (ref 3): p_u_16 ]]
                p_u_15._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                p_u_16:claim_button_pressed()
            end))
            v_u_23:set_visible(false)
            v_u_24 = p_u_16:add_cycle_element(p_u_15, 1, v_u_3:new(v_u_2:new(v_u_22, v_u_21.PrimaryPart, v_u_21.PreviewButton), p_u_15._spui, function() --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_6 ]]
                p_u_15._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            end))
            v_u_24:set_visible(false)
            v_u_26 = v_u_21.MainSurface.SurfaceGui
            v_u_25 = v_u_26.Frame
        end;
        local l_Locked_0 = v_u_7.ChallengePassMissionState.Locked
        v20.update_with_mission = function(_, p27) --[[ Name: update_with_mission ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_25, (ref 3): v_u_4, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_22, (ref 7): v_u_1, (copy 8): p_u_15, (ref 9): l_Locked_0, (ref 10): v_u_7, (ref 11): v_u_5, (ref 12): v_u_8, (ref 13): v_u_12, (ref 14): v_u_13, (ref 15): v_u_14, (ref 16): v_u_10, (ref 17): v_u_11, (ref 18): v_u_9 ]]
            if p27 == nil then
                v_u_26.Enabled = false
                return;
            else
                v_u_26.Enabled = true
                if v_u_25:FindFirstChild("ChallengeNumberDisplay") == nil then
                    v_u_4:warnf("ChallengePassUIElement:update_with_mission _root_frame.ChallengeNumberDisplay does not exist")
                    return;
                else
                    v_u_25.ChallengeNumberDisplay.Text = string.format("Challenge #%d", p27:get_index() + 1)
                    v_u_25.ActiveFrame.Visible = false
                    v_u_25.ClaimedFrame.Visible = false
                    v_u_25.LockedCompletePreviousFrame.Visible = false
                    v_u_25.LockedVIPFrame.Visible = false
                    v_u_23:set_visible(false)
                    v_u_24:set_visible(false)
                    v_u_26.ZOffset = 500 + v_u_22:get_child_id()
                    v_u_25.Back.Image = v_u_1:get_challengepass_item_assetid()
                    v_u_22:set_scale(1)
                    local v28 = p_u_15._player_blob_manager:get_player_blob()
                    l_Locked_0 = v_u_7:playerblob_get_challengepass_mission_state(v28, p27, p_u_15:get_current_dayid())
                    if l_Locked_0 == v_u_7.ChallengePassMissionState.Completed then
                        v_u_25.ClaimedFrame.Visible = true
                    elseif l_Locked_0 == v_u_7.ChallengePassMissionState.Current then
                        v_u_25.ActiveFrame.Visible = true
                        v_u_26.ZOffset = 1000 + v_u_22:get_child_id()
                        v_u_25.Back.Image = v_u_1:get_challengepass_item_selected_assetid()
                        v_u_22:set_scale(1.25)
                    elseif l_Locked_0 == v_u_7.ChallengePassMissionState.CurrentClaimable then
                        v_u_25.ActiveFrame.Visible = true
                        v_u_23:set_visible(true)
                        v_u_26.ZOffset = 1000 + v_u_22:get_child_id()
                        v_u_25.Back.Image = v_u_1:get_challengepass_item_selected_assetid()
                        v_u_22:set_scale(1.25)
                    elseif l_Locked_0 == v_u_7.ChallengePassMissionState.LockedVIP then
                        v_u_25.LockedVIPFrame.Visible = true
                        v_u_24:set_visible(true)
                    elseif l_Locked_0 == v_u_7.ChallengePassMissionState.Locked then
                        v_u_25.LockedCompletePreviousFrame.Visible = true
                        v_u_24:set_visible(true)
                    end;
                    local l_RewardFrame_0 = v_u_25.RewardFrame
                    l_RewardFrame_0.Visible = v_u_25.ActiveFrame.Visible
                    local l_SongIcon_0 = l_RewardFrame_0.SongIcon
                    local l_RewardIcon_0 = l_RewardFrame_0.RewardIcon
                    local l_DescriptionDisplay_0 = l_RewardFrame_0.DescriptionDisplay
                    l_SongIcon_0.Visible = false
                    l_RewardIcon_0.Visible = false
                    local v29 = p27:get_reward_type()
                    local v30 = p27:get_reward_count()
                    local v31 = p27:get_reward_id()
                    if v29 == v_u_7.RewardType.Coins then
                        l_RewardIcon_0.Visible = true
                        l_RewardIcon_0.Image = v_u_1:get_coinstack_large_assetid()
                        l_DescriptionDisplay_0.Text = string.format("%d Coins", v30)
                        return;
                    elseif v29 == v_u_7.RewardType.Stars then
                        l_RewardIcon_0.Visible = true
                        l_RewardIcon_0.Image = v_u_1:get_starstack_large_assetid()
                        l_DescriptionDisplay_0.Text = string.format("%d Stars", v30)
                        return;
                    elseif v_u_7.RewardTypesSong:contains(v29) then
                        l_SongIcon_0.Visible = true
                        v_u_5:singleton():render_coverimage_for_key(l_SongIcon_0.Icon, l_SongIcon_0.IconOverlay, v31)
                        l_DescriptionDisplay_0.Text = string.format("%s (x%d)", v_u_5:singleton():get_title_for_key(v31), v30)
                    elseif v_u_7.RewardTypesMaterial:contains(v29) then
                        l_SongIcon_0.Visible = true
                        l_SongIcon_0.Icon.Visible = true
                        local v32 = false
                        if v29 == v_u_7.RewardType.SmallNotes then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_12:get_small_note_material_ids():random())
                        elseif v29 == v_u_7.RewardType.MediumNotes then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_12:get_medium_note_material_ids():random())
                        elseif v29 == v_u_7.RewardType.LargeNotes then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_12:get_large_note_material_ids():random())
                        elseif v29 == v_u_7.RewardType.Gems then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_12:get_gem_material_ids():random())
                        elseif v29 == v_u_7.RewardType.Tokens then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_12:get_crafting_token_material_ids():random())
                        elseif v29 == v_u_7.RewardType.UpgradeBoosts then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_13:singleton():get_upgrade_boost_material_id())
                        elseif v29 == v_u_7.RewardType.UpgradeProtects then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v_u_13:singleton():get_upgrade_protect_material_id())
                        elseif v29 == v_u_7.RewardType.Material then
                            l_SongIcon_0.Icon.Image = v_u_8:singleton():get_material_icon(v31)
                            l_DescriptionDisplay_0.Text = string.format("%s (x%d)", v_u_8:singleton():get_material_name(v31), v30)
                            v32 = true
                        end;
                        l_SongIcon_0.IconOverlay.Visible = false
                        if v32 == false then
                            l_DescriptionDisplay_0.Text = string.format("%s (x%d)", v_u_7:reward_type_to_name(v29), v30)
                            return;
                        end;
                    else
                        if v_u_7.RewardTypesDance:contains(v29) then
                            if v_u_14:get_owned_danceid_to_equipped_dict(v28):contains(v31) then
                                local _, v33, _ = v_u_7:get_owned_dance_challengepass_reward()
                                l_RewardIcon_0.Visible = true
                                l_RewardIcon_0.Image = v_u_1:get_starstack_large_assetid()
                                l_DescriptionDisplay_0.Text = string.format("%d Stars (Owned Dance)", v33)
                            else
                                l_RewardIcon_0.Visible = true
                                l_RewardIcon_0.Image = v_u_10:singleton():get_dance_icon_for_id(v31)
                                l_DescriptionDisplay_0.Text = string.format("%s (Dance)", v_u_10:singleton():get_dance_name_for_id(v31))
                            end;
                        end;
                        if v_u_7.RewardTypesTitle:contains(v29) then
                            l_RewardIcon_0.Visible = true
                            l_RewardIcon_0.Image = v_u_1:get_hud_button_chat_assetid()
                            l_DescriptionDisplay_0.Text = string.format("%s (Title)", v_u_11:singleton():get_title_name_for_id(v31))
                            return;
                        end;
                        if v_u_7.RewardTypesGear:contains(v29) then
                            local v34 = v_u_9:singleton():get_equipment_for_id(v31)
                            l_SongIcon_0.Visible = true
                            l_SongIcon_0.Icon.Visible = true
                            l_SongIcon_0.Icon.Image = v34:get_icon()
                            l_SongIcon_0.IconOverlay.Visible = false
                            l_DescriptionDisplay_0.Text = string.format("%s", v34:get_name())
                        end;
                    end;
                end;
            end;
        end;
        v20.set_visible = function(_, p35) --[[ Name: set_visible ]] --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_23, (ref 3): v_u_24 ]]
            v_u_25.Visible = p35
            if p35 ~= true then
                v_u_23:set_visible(p35)
                v_u_24:set_visible(p35)
            end;
        end;
        v20.layout = function(_) --[[ Name: layout ]] --[[ Line: 212 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22:layout()
        end;
        v20.behaviour_update = function(_, _) --[[ Name: behaviour_update ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): l_Locked_0, (ref 2): v_u_7, (ref 3): v_u_24, (ref 4): v_u_25 ]]
            if l_Locked_0 == v_u_7.ChallengePassMissionState.LockedVIP then
                if v_u_24:get_selected() then
                    v_u_25.RewardFrame.Visible = true
                    v_u_25.LockedVIPFrame.Visible = false
                else
                    v_u_25.RewardFrame.Visible = false
                    v_u_25.LockedVIPFrame.Visible = true
                end;
            else
                if l_Locked_0 == v_u_7.ChallengePassMissionState.Locked then
                    if v_u_24:get_selected() then
                        v_u_25.RewardFrame.Visible = true
                        v_u_25.LockedCompletePreviousFrame.Visible = false
                        return;
                    end;
                    v_u_25.RewardFrame.Visible = false
                    v_u_25.LockedCompletePreviousFrame.Visible = true
                end;
                return;
            end;
        end;
        v20:cons()
        return v20;
    end
};
