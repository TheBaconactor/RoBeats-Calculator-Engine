-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_5 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_33 = {
    ["RecruitmentState"] = {
        ["RecruitingMustApprove"] = 0,
        ["RecruitingAutoAccept"] = 1,
        ["NotRecruiting"] = 2
    },
    ["MemberInfo"] = {},
    ["WeekContributionEntry"] = {},
    ["get_player_info"] = function(_, p8, p9) --[[ Name: get_player_info ]] --[[ Line: 280 ]]
        local v10 = p8:get_member_infos()
        local v11 = nil
        for v12 = 1, v10:count() do
            local v13 = v10:get(v12)
            if v13:get_rbxid() == p9 then
                return v13;
            end;
        end;
        return v11;
    end,
    ["playerid_set"] = function(_, p14) --[[ Name: playerid_set ]] --[[ Line: 315 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v15 = v_u_1:new()
        local v16 = p14:get_member_infos()
        for v17 = 1, v16:count() do
            v15:add(v16:get(v17):get_rbxid(), true)
        end;
        return v15;
    end,
    ["member_can_kick_member"] = function(_, p18, p19) --[[ Name: member_can_kick_member ]] --[[ Line: 325 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        if p18:get_rbxid() == p19:get_rbxid() then
            return true;
        end;
        local v20 = p18:get_rank()
        return v20 == v_u_4.Owner and true or v20 == v_u_4.Admin and p19:get_rank() == v_u_4.Member;
    end,
    ["render_guild_icon"] = function(_, p21, p22) --[[ Name: render_guild_icon ]] --[[ Line: 358 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        if #p21:get_icon() > 0 then
            p22.Image = p21:get_icon()
        else
            p22.Image = v_u_6:placeholder_assetid()
        end;
    end,
    ["get_owner"] = function(_, p23) --[[ Name: get_owner ]] --[[ Line: 366 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v24 = nil
        for _, v25 in p23:get_member_infos():key_itr() do
            if v25:get_rank() == v_u_4.Owner then
                return v25;
            end;
        end;
        return v24;
    end,
    ["get_member_count_with_join_date_older_than_current_week"] = function(_, p26) --[[ Name: get_member_count_with_join_date_older_than_current_week ]] --[[ Line: 377 ]]
        local v27 = p26:get_member_infos()
        local v28 = p26:get_current_week_contribution_entry():get_week_id()
        local v29 = 0
        for v30 = 1, v27:count() do
            if v27:get(v30):get_joined_week() < v28 then
                v29 = v29 + 1
            end;
        end;
        return v29;
    end,
    ["clear_private_data"] = function(_, p31) --[[ Name: clear_private_data ]] --[[ Line: 414 ]]
        for _, v32 in p31:get_member_infos():key_itr() do
            v32:set_joined_week(0)
            v32:set_current_week_contribution_points(0)
            v32:set_last_week_contribution_points(0)
        end;
        p31:set_star_currency(0)
        p31:set_bonus_weekid(0)
        p31:set_bonus_flag(0)
    end
}
local v_u_34 = {
    ["RecruitingMustApprove"] = 0,
    ["RecruitingAutoAccept"] = 1,
    ["NotRecruiting"] = 2
}
v_u_33.new = function(_, p_u_35) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_33, (copy 5): v_u_34 ]]
    v_u_3:is_int_greater_than(p_u_35, v_u_5:not_in_guild_id())
    local v36 = {}
    local v_u_37 = v_u_2:new()
    local v_u_38 = ""
    local v_u_39 = ""
    local v_u_40 = ""
    local v_u_41 = 0
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = 0
    local v_u_45 = 0
    local l_RecruitingMustApprove_0 = v_u_33.RecruitmentState.RecruitingMustApprove
    v36.set_default_contribution_entry_info = function(_) --[[ Name: set_default_contribution_entry_info ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_33, (ref 3): v_u_43 ]]
        v_u_42 = v_u_33.WeekContributionEntry:default_value()
        v_u_43 = v_u_33.WeekContributionEntry:default_value()
    end;
    v36:set_default_contribution_entry_info()
    v36.get_guildid = function(_) --[[ Name: get_guildid ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): p_u_35 ]]
        return p_u_35;
    end;
    v36.get_member_infos = function(_) --[[ Name: get_member_infos ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return v_u_37;
    end;
    v36.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v36.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        return v_u_39;
    end;
    v36.get_message = function(_) --[[ Name: get_message ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40;
    end;
    v36.get_star_currency = function(_) --[[ Name: get_star_currency ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41;
    end;
    v36.get_current_week_contribution_entry = function(_) --[[ Name: get_current_week_contribution_entry ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42;
    end;
    v36.get_last_week_contribution_entry = function(_) --[[ Name: get_last_week_contribution_entry ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v36.get_bonus_weekid = function(_) --[[ Name: get_bonus_weekid ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44;
    end;
    v36.get_bonus_flag = function(_) --[[ Name: get_bonus_flag ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_45 ]]
        return v_u_45;
    end;
    v36.get_recruitment_state = function(_) --[[ Name: get_recruitment_state ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): l_RecruitingMustApprove_0 ]]
        return l_RecruitingMustApprove_0;
    end;
    v36.get_total_members = function(_) --[[ Name: get_total_members ]] --[[ Line: 56 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return v_u_37:count();
    end;
    v36.set_name = function(_, p46) --[[ Name: set_name ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_38 ]]
        v_u_3:is_string(p46)
        v_u_38 = p46
    end;
    v36.set_icon = function(_, p47) --[[ Name: set_icon ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_39 ]]
        v_u_3:is_string(p47)
        v_u_39 = p47
    end;
    v36.set_message = function(_, p48) --[[ Name: set_message ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_40 ]]
        v_u_3:is_string(p48)
        v_u_40 = p48
    end;
    v36.set_star_currency = function(_, p49) --[[ Name: set_star_currency ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_41 ]]
        v_u_3:is_int_greater_than(p49, 0)
        v_u_41 = p49
    end;
    v36.set_current_week_contribution_entry = function(_, p50) --[[ Name: set_current_week_contribution_entry ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_42 ]]
        v_u_3:is_bool(p50:is_entered())
        v_u_42 = p50
    end;
    v36.set_last_week_contribution_entry = function(_, p51) --[[ Name: set_last_week_contribution_entry ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_43 ]]
        v_u_3:is_bool(p51:is_entered())
        v_u_43 = p51
    end;
    v36.set_bonus_weekid = function(_, p52) --[[ Name: set_bonus_weekid ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_44 ]]
        v_u_3:is_int(p52)
        v_u_44 = p52
    end;
    v36.set_bonus_flag = function(_, p53) --[[ Name: set_bonus_flag ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_45 ]]
        v_u_3:is_int(p53)
        v_u_45 = p53
    end;
    v36.set_recruitment_state = function(_, p54) --[[ Name: set_recruitment_state ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_34, (ref 3): l_RecruitingMustApprove_0 ]]
        v_u_3:is_enum_member(p54, v_u_34)
        l_RecruitingMustApprove_0 = p54
    end;
    v36.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): v_u_37, (copy 2): p_u_35, (ref 3): v_u_38, (ref 4): v_u_39, (ref 5): v_u_40, (ref 6): v_u_41, (ref 7): v_u_42, (ref 8): v_u_43, (ref 9): v_u_44, (ref 10): v_u_45, (ref 11): l_RecruitingMustApprove_0 ]]
        local v55 = {}
        for v56 = 1, v_u_37:count() do
            v55[v56] = v_u_37:get(v56):to_table()
        end;
        return {
            ["Version"] = 2,
            ["GuildId"] = p_u_35,
            ["Info"] = {
                ["Name"] = v_u_38,
                ["Icon"] = v_u_39,
                ["Message"] = v_u_40
            },
            ["MemberInfo"] = v55,
            ["StarCurrency"] = v_u_41,
            ["CurrentWeekContributionInfo"] = v_u_42:to_table(),
            ["LastWeekContributionInfo"] = v_u_43:to_table(),
            ["BonusWeekID"] = v_u_44,
            ["BonusFlag"] = v_u_45,
            ["RecruitmentState"] = l_RecruitingMustApprove_0
        };
    end;
    return v36;
end;
v_u_33.MemberInfo.new = function(_, p_u_57, p_u_58, p_u_59) --[[ Name: new ]] --[[ Line: 95 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4 ]]
    v_u_3:is_int(p_u_57)
    v_u_3:is_string(p_u_58)
    v_u_3:is_enum_member(p_u_59, v_u_4)
    local v_u_60 = 0
    local v_u_61 = 0
    local v_u_62 = 0
    local v65 = {
        ["get_joined_week"] = function(_) --[[ Name: get_joined_week ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_60 ]]
            return v_u_60;
        end,
        ["get_current_week_contribution_points"] = function(_) --[[ Name: get_current_week_contribution_points ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_61 ]]
            return v_u_61;
        end,
        ["get_last_week_contribution_points"] = function(_) --[[ Name: get_last_week_contribution_points ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_62 ]]
            return v_u_62;
        end,
        ["set_current_week_contribution_points"] = function(_, p63) --[[ Name: set_current_week_contribution_points ]] --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_61 ]]
            v_u_61 = p63 < 0 and 0 or p63
        end,
        ["set_last_week_contribution_points"] = function(_, p64) --[[ Name: set_last_week_contribution_points ]] --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_62 ]]
            v_u_62 = p64 < 0 and 0 or p64
        end
    }
    v65.get_rbxid = function(_) --[[ Name: get_rbxid ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): p_u_57 ]]
        return p_u_57;
    end;
    v65.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): p_u_58 ]]
        return p_u_58;
    end;
    v65.get_rank = function(_) --[[ Name: get_rank ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): p_u_59 ]]
        return p_u_59;
    end;
    v65.set_name = function(_, p66) --[[ Name: set_name ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_58 ]]
        v_u_3:is_string(p66)
        p_u_58 = p66
    end;
    v65.set_rank = function(_, p67) --[[ Name: set_rank ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): p_u_59 ]]
        v_u_3:is_enum_member(p67, v_u_4)
        p_u_59 = p67
    end;
    v65.set_joined_week = function(_, p68) --[[ Name: set_joined_week ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_60 ]]
        v_u_3:is_int_greater_than(p68, 0)
        v_u_60 = p68
    end;
    v65.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 125 ]]
        --[[ Upvalues: (copy 1): p_u_57, (ref 2): p_u_58, (ref 3): p_u_59, (ref 4): v_u_60, (ref 5): v_u_61, (ref 6): v_u_62 ]]
        return {
            ["Version"] = 2,
            ["RbxId"] = p_u_57,
            ["Name"] = p_u_58,
            ["Rank"] = p_u_59,
            ["JoinedWeek"] = v_u_60,
            ["CurrentWeekContribution"] = v_u_61,
            ["LastWeekContribution"] = v_u_62
        };
    end;
    return v65;
end;
v_u_33.MemberInfo.from_table = function(_, p69) --[[ Name: from_table ]] --[[ Line: 140 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v70 = v_u_33.MemberInfo:new(p69.RbxId, p69.Name, p69.Rank)
    if p69.Version ~= nil and p69.Version >= 2 then
        v70:set_joined_week(p69.JoinedWeek)
        v70:set_current_week_contribution_points(p69.CurrentWeekContribution)
        v70:set_last_week_contribution_points(p69.LastWeekContribution)
    end;
    return v70;
end;
v_u_33.WeekContributionEntry.new = function(_, p_u_71, p_u_72, p_u_73, p_u_74, p_u_75, p_u_76) --[[ Name: new ]] --[[ Line: 151 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7 ]]
    v_u_3:is_bool(p_u_71)
    v_u_3:is_int_greater_than(p_u_72, 0)
    v_u_3:is_enum_member(p_u_73, v_u_7)
    v_u_3:is_int_greater_than(p_u_74, 0)
    v_u_3:is_int(p_u_75)
    v_u_3:is_int(p_u_76)
    local v79 = {
        ["set_rank_from_list_index"] = function(p77, p78) --[[ Name: set_rank_from_list_index ]] --[[ Line: 176 ]]
            p77:set_rank(p78 - 1)
        end
    }
    v79.is_entered = function(_) --[[ Name: is_entered ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): p_u_71 ]]
        return p_u_71;
    end;
    v79.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 162 ]]
        --[[ Upvalues: (copy 1): p_u_72 ]]
        return p_u_72;
    end;
    v79.get_selected_color = function(_) --[[ Name: get_selected_color ]] --[[ Line: 163 ]]
        --[[ Upvalues: (ref 1): p_u_73 ]]
        return p_u_73;
    end;
    v79.get_contribution_points = function(_) --[[ Name: get_contribution_points ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): p_u_74 ]]
        return p_u_74;
    end;
    v79.get_rank = function(_) --[[ Name: get_rank ]] --[[ Line: 165 ]]
        --[[ Upvalues: (ref 1): p_u_75 ]]
        return p_u_75;
    end;
    v79.get_total_entries = function(_) --[[ Name: get_total_entries ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): p_u_76 ]]
        return p_u_76;
    end;
    v79.set_entered = function(_, p80) --[[ Name: set_entered ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_71 ]]
        v_u_3:is_bool(p80)
        p_u_71 = p80
    end;
    v79.set_selected_color = function(_, p81) --[[ Name: set_selected_color ]] --[[ Line: 169 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_7, (ref 3): p_u_73 ]]
        v_u_3:is_enum_member(p81, v_u_7)
        p_u_73 = p81
    end;
    v79.set_contribution_points = function(_, p82) --[[ Name: set_contribution_points ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_74 ]]
        v_u_3:is_int(p82)
        p_u_74 = p82 < 0 and 0 or p82
    end;
    v79.set_rank = function(_, p83) --[[ Name: set_rank ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_75 ]]
        v_u_3:is_int(p83)
        p_u_75 = p83
    end;
    v79.set_total_entries = function(_, p84) --[[ Name: set_total_entries ]] --[[ Line: 180 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_76 ]]
        v_u_3:is_int(p84)
        p_u_76 = p84
    end;
    v79.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 182 ]]
        --[[ Upvalues: (ref 1): p_u_71, (copy 2): p_u_72, (ref 3): p_u_73, (ref 4): p_u_74, (ref 5): p_u_75, (ref 6): p_u_76 ]]
        return {
            ["Version"] = 1,
            ["IsEntered"] = p_u_71,
            ["WeekId"] = p_u_72,
            ["SelectedColor"] = p_u_73,
            ["ContributionPointsTotal"] = p_u_74,
            ["Rank"] = p_u_75,
            ["Total"] = p_u_76
        };
    end;
    return v79;
end;
v_u_33.WeekContributionEntry.from_table = function(_, p85) --[[ Name: from_table ]] --[[ Line: 197 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return v_u_33.WeekContributionEntry:new(p85.IsEntered, p85.WeekId, p85.SelectedColor, p85.ContributionPointsTotal, p85.Rank, p85.Total);
end;
v_u_33.WeekContributionEntry.default_value = function(_) --[[ Name: default_value ]] --[[ Line: 209 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_7 ]]
    return v_u_33.WeekContributionEntry:new(false, 0, v_u_7.Blue, 0, 0, 0);
end;
v_u_33.from_table = function(_, p86) --[[ Name: from_table ]] --[[ Line: 221 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_3, (copy 3): v_u_34 ]]
    local v87 = v_u_33:new(p86.GuildId)
    v87:set_name(p86.Info.Name)
    v87:set_icon(p86.Info.Icon)
    v87:set_message(p86.Info.Message)
    local l_MemberInfo_0 = p86.MemberInfo
    for v88 = 1, #l_MemberInfo_0 do
        v87:get_member_infos():push_back((v_u_33.MemberInfo:from_table(l_MemberInfo_0[v88])))
    end;
    if p86.Version ~= nil and p86.Version >= 2 then
        v87:set_star_currency(p86.StarCurrency)
        local l_CurrentWeekContributionInfo_0 = p86.CurrentWeekContributionInfo
        v87:set_current_week_contribution_entry(v_u_33.WeekContributionEntry:new(l_CurrentWeekContributionInfo_0.IsEntered, l_CurrentWeekContributionInfo_0.WeekId, l_CurrentWeekContributionInfo_0.SelectedColor, l_CurrentWeekContributionInfo_0.ContributionPointsTotal, l_CurrentWeekContributionInfo_0.Rank, l_CurrentWeekContributionInfo_0.Total))
        local l_LastWeekContributionInfo_0 = p86.LastWeekContributionInfo
        v87:set_last_week_contribution_entry(v_u_33.WeekContributionEntry:new(l_LastWeekContributionInfo_0.IsEntered, l_LastWeekContributionInfo_0.WeekId, l_LastWeekContributionInfo_0.SelectedColor, l_LastWeekContributionInfo_0.ContributionPointsTotal, l_LastWeekContributionInfo_0.Rank, l_LastWeekContributionInfo_0.Total))
    end;
    if typeof(p86.BonusWeekID) == "number" then
        v87:set_bonus_weekid(p86.BonusWeekID)
    end;
    if typeof(p86.BonusFlag) == "number" then
        v87:set_bonus_flag(p86.BonusFlag)
    end;
    if v_u_3:test_enum_member(p86.RecruitmentState, v_u_34) then
        v87:set_recruitment_state(p86.RecruitmentState)
    end;
    return v87;
end;
v_u_33.table_list_to_list = function(_, p89) --[[ Name: table_list_to_list ]] --[[ Line: 270 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_33 ]]
    local v90 = v_u_2:new()
    for v91 = 1, #p89 do
        v90:push_back(v_u_33:from_table(p89[v91]))
    end;
    return v90;
end;
v_u_33.get_or_create_player_info = function(_, p92, p93, p94) --[[ Name: get_or_create_player_info ]] --[[ Line: 293 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_4 ]]
    local v95 = v_u_33:get_player_info(p92, p93)
    if v95 ~= nil then
        return v95;
    end;
    local v96 = v_u_33.MemberInfo:new(p93, p94, v_u_4.Member)
    p92:get_member_infos():push_back(v96)
    return v96;
end;
v_u_33.player_has_admin_access = function(_, p97, p98) --[[ Name: player_has_admin_access ]] --[[ Line: 304 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_4 ]]
    local v99 = v_u_33:get_player_info(p97, p98)
    if v99 ~= nil then
        local v100 = v99:get_rank()
        if v100 == v_u_4.Admin or v100 == v_u_4.Owner then
            return true;
        end;
    end;
    return false;
end;
v_u_33.member_playerblob_can_claim_weekly_buff = function(_, p101, p102, p103) --[[ Name: member_playerblob_can_claim_weekly_buff ]] --[[ Line: 339 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_33 ]]
    local v104 = p101:get_last_week_contribution_entry()
    local v105 = v104:get_week_id() + 1
    if v105 <= v_u_5:playerblob_get_team_buff_weekid(p102) then
        return false, "Already claimed bonus for this week", v105;
    elseif v104:is_entered() == true then
        if v_u_33:get_player_info(p101, p103):get_joined_week() > v104:get_week_id() then
            return false, "Joined team after the week concluded", v105;
        else
            return true, "", v105;
        end;
    else
        return false, "Team did not enter last week", v105;
    end;
end;
v_u_33.get_recruitment_state_name = function(_, p106) --[[ Name: get_recruitment_state_name ]] --[[ Line: 390 ]]
    --[[ Upvalues: (copy 1): v_u_34 ]]
    return p106 == v_u_34.NotRecruiting and "Not Recruiting" or (p106 == v_u_34.RecruitingAutoAccept and "Auto Accept" or (p106 == v_u_34.RecruitingMustApprove and "Manual Approval" or "?"));
end;
v_u_33.get_recruitment_state_description = function(_, p107) --[[ Name: get_recruitment_state_description ]] --[[ Line: 402 ]]
    --[[ Upvalues: (copy 1): v_u_34 ]]
    return p107 == v_u_34.NotRecruiting and "Not visible on the team recruitment board for players on your server." or (p107 == v_u_34.RecruitingAutoAccept and "Automatically accept join requests from players on your server." or (p107 == v_u_34.RecruitingMustApprove and "An admin must manually accept join requests from players on your server." or "?"));
end;
return v_u_33;
